import type { ReactNode } from "react";
import styles from "./Panel.module.scss";

interface Props {
  title: string;
  className?: string;
  children: ReactNode;
}

export function Panel({ title, className, children }: Props) {
  return (
    <section className={[styles.panel, className].filter(Boolean).join(" ")}>
      <h2 className={styles.title}>{title}</h2>
      {children}
    </section>
  );
}
