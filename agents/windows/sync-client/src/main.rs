//! Validation spike: does `snapcast-client` actually work against our real
//! snapserver? Connects, receives the `pc` stream, decodes it, and plays it
//! out this PC's normal default output device (NOT VB-CABLE yet - that's a
//! separate concern for later).
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
use std::sync::atomic::{AtomicI64, Ordering};
use std::sync::{Arc, Mutex};

use cpal::traits::{DeviceTrait, HostTrait, StreamTrait};
use snapcast_client::{ClientConfig, ClientEvent, SnapClient};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let host = std::env::args().nth(1).unwrap_or_else(|| "192.168.1.4".to_string());

    let config = ClientConfig {
        host: host.clone(),
        port: 1704,
        client_name: "sound-assistant-rs-spike".to_string(),
        ..Default::default()
    };

    println!("connecting to snapserver at {host}:1704 ...");
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
            println!("event: {event:?}");
        }
    });

    let buffer: Arc<Mutex<VecDeque<f32>>> = Arc::new(Mutex::new(VecDeque::new()));
    let mut stream_handle: Option<cpal::Stream> = None;
    let mut opened_rate: Option<u32> = None;
    let mut opened_channels: Option<u16> = None;

    let buffer_for_audio = buffer.clone();
    let audio_task = tokio::spawn(async move {
        let cpal_host = cpal::default_host();
        let device = cpal_host
            .default_output_device()
            .expect("no default output device");

        // How many samples to accumulate before letting cpal start pulling
        // from the buffer at all, so the callback never starts against an
        // empty buffer (which sounds like sputtering).
        const PRIME_MS: usize = 200;

        while let Some(frame) = audio_rx.recv().await {
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
                    frame.sample_rate as usize * frame.channels as usize * PRIME_MS / 1000;
                if buffer_for_audio.lock().unwrap().len() < primed_len {
                    continue;
                }

                println!(
                    "opening cpal stream: {} Hz, {} ch (primed with {PRIME_MS}ms)",
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
                        |err| eprintln!("cpal stream error: {err}"),
                        None,
                    )
                    .expect("failed to build output stream");
                stream.play().expect("failed to start stream");
                stream_handle = Some(stream);
            }
        }
        println!("audio channel closed");
    });

    println!("running client (Ctrl+C to stop)...");
    tokio::select! {
        result = client.run() => {
            println!("client.run() returned: {result:?}");
        }
        _ = audio_task => {
            println!("audio task ended");
        }
        _ = tokio::signal::ctrl_c() => {
            println!("stopping");
        }
    }

    Ok(())
}
