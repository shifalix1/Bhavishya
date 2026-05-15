import styles from "./WhatIsDarpan.module.css";

export default function WhatIsDarpan({ onBack }) {
  return (
    <div className={styles.wrap}>
      <button className={styles.backBtn} onClick={onBack}>
        Back
      </button>

      <div className={styles.badge}>Understanding Bhavishya</div>

      <h2 className={styles.heading}>What Bhavishya actually does</h2>
      <p className={styles.subhead}>
        Bhavishya means <em>future</em> in Hindi. The tool is named after what
        it helps you see.
      </p>

      <div className={styles.blocks}>
        <Block
          num="01"
          title="Aawaz listens without judging"
          subtitle="Aawaz = Voice"
          body="Aawaz has a conversation with you — what you enjoy, what bores you, what your family expects, what scares you. There is no right answer. It speaks back in Hindi, English, or Hinglish."
        />
        <Block
          num="02"
          title="Darpan builds your identity fingerprint"
          subtitle="Darpan = Mirror"
          body="From your words, Darpan extracts your thinking style, core values, hidden strengths, active fears, and family pressure map. This is not a personality test. It is a mirror."
        />
        <Block
          num="03"
          title="Bhavishya Core shows three honest futures"
          subtitle="Set in 2031"
          body="After your first session, the system simulates three parallel life paths grounded in real Indian career data, specific to who you actually are — not who your school says you should be."
        />
        <Block
          num="04"
          title="Margdarshak guides you"
          subtitle="Margdarshak = Guide"
          body="Your ongoing AI counsellor. Ask anything about career confusion, stream selection, or family pressure. It knows your identity fingerprint and responds accordingly."
        />
        <Block
          num="05"
          title="It remembers you across sessions"
          subtitle="Longitudinal tracking"
          body="Every session updates your fingerprint. Over time, Bhavishya tracks how you change, shows you what shifted, what stayed the same, and why that matters for your decisions."
        />
      </div>

      <div className={styles.privacy}>
        Your conversation text is sent to our server to generate your
        fingerprint. No email, no tracking. Everything is linked only to your
        username and PIN.
      </div>

      <button className={styles.startBtn} onClick={onBack}>
        Got it, start now
      </button>
    </div>
  );
}

function Block({ num, title, subtitle, body }) {
  return (
    <div className={styles.block}>
      <span className={styles.blockNum}>{num}</span>
      <div className={styles.blockContent}>
        <div className={styles.blockTitle}>{title}</div>
        {subtitle && <div className={styles.blockSubtitle}>{subtitle}</div>}
        <div className={styles.blockBody}>{body}</div>
      </div>
    </div>
  );
}
