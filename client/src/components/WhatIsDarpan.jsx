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
          body="Aawaz has a conversation with you — what you enjoy, what bores you, what your family expects, what scares you. There is no right answer. It speaks back in Hindi, English, or Hinglish. You can also share an image and Aawaz will read it as part of your story."
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
          subtitle="Your life, years from now."
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
        <Block
          num="06"
          title="Built on Gemma 4, Google's open model"
          subtitle="Why Gemma specifically — not GPT, not Gemini"
          body="Three reasons. First, Gemma 4's tokenizer handles Hinglish natively — mixed Hindi-English text is tokenized as one language, not two, so the model reads student input the way a real counsellor would hear it. Second, Gemma 4 is multimodal: when a student shares an image in Aawaz, the same model that runs the conversation also reads the image — no separate vision pipeline. Third, Gemma is open-weights, which makes the local deployment path below possible."
        />
        <Block
          num="07"
          title="Runs offline on a school laptop"
          subtitle="Gemma 4 E4B via Ollama — no internet required"
          body="Set BHAVISHYA_MODE=local and the entire system switches to Gemma 4 E4B running on-device via Ollama. A school in Nagpur or a coaching centre in Patna with no cloud budget can deploy this on a Rs.40,000 laptop and give every student the same experience. This is what 'Good' means in Gemma 4 Good — the model being open is what makes access possible."
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
