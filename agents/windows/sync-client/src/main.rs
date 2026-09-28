//! Custom Snapcast client for the Windows sync toggle (DESIGN.md section
//! 15). Connects to a real snapserver, decodes the stream, and plays it
//! to a specific output device - normally the *real* hardware device,
//! since the whole point of this toggle is that the system default has
//! been switched to VB-CABLE and `capture.py` is now capturing from
//! there instead (see agents/windows/sync_controller.py).
//!
//! The crate's public `audio_rx` path forwards decoded audio immediately,
//! with no reference to the server's clock offset or buffer setting (its
//! internal `Stream`/`get_player_chunk` scheduler exists but isn't wired to
//! that path - see docs/status.md). So this CLI does the scheduling itself:
//! for each frame, compute when the server intends it to play
//! (frame.timestamp_usec + buffer_ms), translate that into our own clock
//! domain using the already-public `client.time_provider`, and sleep until
//! that instant before handing it to cpal.

use std::collections::VecDeque;
use std::io::Write;
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Mutex};

use clap::Parser;
use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use snapcast_client::{ClientConfig, ClientEvent, SnapClient};

/// `println!`/`eprintln!` only auto-flush promptly when stdout/stderr is
/// detected as a real interactive terminal. Spawned as a subprocess via
/// Python's `subprocess.Popen` (as this always is - see
/// agents/windows/sync_controller.py), that detection can fail, silently
/// leaving every line stuck in an internal buffer forever - so nothing
/// ever reaches the parent agent's console, not even on a real failure.
/// Flush explicitly instead of trusting line-buffering to kick in.
macro_rules! log {
    ($($arg:tt)*) => {{
        println!($($arg)*);
        let _ = std::io::stdout().flush();
    }};
}

macro_rules! log_err {
    ($($arg:tt)*) => {{
        eprintln!($($arg)*);
        let _ = std::io::stderr().flush();
    }};
}

#[derive(Parser)]
struct Args {
    /// snapserver host
    #[arg(long, default_value = "192.168.1.4")]
    host: String,

    /// snapserver stream port
    #[arg(long, default_value_t = 1704)]
    port: u16,

    /// Output device name (substring match, case-insensitive). Defaults
    /// to whatever the OS currently considers the default output device -
    /// which is the *wrong* thing once the sync toggle has switched that
    /// to VB-CABLE, so the toggle always passes this explicitly.
    #[arg(long)]
    device: Option<String>,

    /// Client name sent to the server in the Snapcast Hello handshake.
    #[arg(long, default_value = "sound-assistant-sync-client")]
    client_name: String,
}

fn device_name(device: &cpal::Device) -> String {
    device
        .description()
        .map(|d| d.name().to_string())
        .unwrap_or_else(|_| "<unknown>".to_string())
}

fn find_output_device(host: &cpal::Host, name_substring: &str) -> cpal::Device {
    let needle = name_substring.to_lowercase();
    host.output_devices()
        .expect("failed to enumerate output devices")
        .find(|d| device_name(d).to_lowercase().contains(&needle))
        .unwrap_or_else(|| panic!("no output device matching {name_substring:?}"))
}

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args = Args::parse();
    let host = args.host;

    let config = ClientConfig {
        host: host.clone(),
        port: args.port,
        client_name: args.client_name,
        ..Default::default()
    };

    log!("connecting to snapserver at {host}:{} ...", args.port);
    let (mut client, mut events, mut audio_rx) = SnapClient::new(config);

    // Cloned out before client.run() takes &mut client, so the audio task
    // can read the live clock offset independently.
    let time_provider = client.time_provider.clone();

    // buffer_ms comes from the server (ServerSettings); shared with the
    // audio task via a plain atomic. Defaults to Snapcast's own default.
    let buffer_ms: Arc<AtomicI64> = Arc::new(AtomicI64::new(1000));
    let buffer_ms_for_events = buffer_ms.clone();
    tokio::spawn(async move {
        while let Some(event) = events.recv().await {
            if let ClientEvent::ServerSettings { buffer_ms, .. } = &event {
                buffer_ms_for_events.store(*buffer_ms as i64, Ordering::Relaxed);
            }
            log!("event: {event:?}");
        }
    });

    let buffer: Arc<Mutex<VecDeque<f32>>> = Arc::new(Mutex::new(VecDeque::new()));
    let mut stream_handle: Option<cpal::Stream> = None;
    let mut opened_rate: Option<u32> = None;
    let mut opened_channels: Option<u16> = None;

    let buffer_for_audio = buffer.clone();
    let device_filter = args.device;
    let audio_task = tokio::spawn(async move {
        let cpal_host = cpal::default_host();
        let device = match &device_filter {
            Some(name) => find_output_device(&cpal_host, name),
            None => cpal_host
                .default_output_device()
                .expect("no default output device"),
        };
        log!("output device: {}", device_name(&device));

        while let Some(frame) = audio_rx.recv().await {
            // How many samples to accumulate before letting cpal start
            // pulling from the buffer at all, so the callback never starts
            // against an empty buffer (which sounds like sputtering).
            // Tracks the server's live buffer_ms rather than a fixed
            // constant - a hardcoded value here would itself become the
            // bottleneck once buffer_ms drops below it, and could cause a
            // startup hiccup. Half of buffer_ms, with a small floor so it's
            // never literally zero.
            let prime_ms = (buffer_ms.load(Ordering::Relaxed) / 2).clamp(20, 300) as usize;
            // Schedule this frame against the server's intended play time,
            // translated into our own clock domain.
            let offset_usec = time_provider.lock().unwrap().diff_to_server_usec();
            let target_server_usec =
                frame.timestamp_usec + buffer_ms.load(Ordering::Relaxed) * 1000;
            let target_local_usec = target_server_usec - offset_usec;
            let now_usec = snapcast_proto::time::now_usec();
            let wait_usec = target_local_usec - now_usec;
            if wait_usec > 0 {
                tokio::time::sleep(std::time::Duration::from_micros(wait_usec as u64)).await;
            }

            let format_changed =
                opened_rate != Some(frame.sample_rate) || opened_channels != Some(frame.channels);
            if format_changed {
                stream_handle = None;
                opened_rate = Some(frame.sample_rate);
                opened_channels = Some(frame.channels);
            }

            {
                let mut buf = buffer_for_audio.lock().unwrap();
                buf.extend(frame.samples.iter().copied());
                while buf.len() > frame.sample_rate as usize * frame.channels as usize * 2 {
                    buf.pop_front();
                }
            }

            if stream_handle.is_none() {
                let primed_len =
                    frame.sample_rate as usize * frame.channels as usize * prime_ms / 1000;
                if buffer_for_audio.lock().unwrap().len() < primed_len {
                    continue;
                }

                log!(
                    "opening cpal stream: {} Hz, {} ch (primed with {prime_ms}ms)",
                    frame.sample_rate, frame.channels
                );
                let stream_config = cpal::StreamConfig {
                    channels: frame.channels,
                    sample_rate: frame.sample_rate,
                    buffer_size: cpal::BufferSize::Default,
                };
                let cb_buffer = buffer_for_audio.clone();
                let stream = device
                    .build_output_stream(
                        stream_config,
                        move |data: &mut [f32], _| {
                            let mut buf = cb_buffer.lock().unwrap();
                            for sample in data.iter_mut() {
                                *sample = buf.pop_front().unwrap_or(0.0);
                            }
                        },
                        |err| log_err!("cpal stream error: {err}"),
                        None,
                    )
                    .expect("failed to build output stream");
                stream.play().expect("failed to start stream");
                stream_handle = Some(stream);
            }
        }
        log!("audio channel closed");
    });

    log!("running client (Ctrl+C to stop)...");
    tokio::select! {
        result = client.run() => {
            log!("client.run() returned: {result:?}");
        }
        _ = audio_task => {
            log!("audio task ended");
        }
        _ = tokio::signal::ctrl_c() => {
            log!("stopping");
        }
    }

    Ok(())
}
