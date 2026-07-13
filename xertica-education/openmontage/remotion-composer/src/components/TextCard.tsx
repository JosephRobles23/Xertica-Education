import { AbsoluteFill, spring, useCurrentFrame, useVideoConfig } from "remotion";

interface TextCardProps {
  text: string;
  subtitle?: string;
  fontSize?: number;
  color?: string;
  backgroundColor?: string;
}

export const TextCard: React.FC<TextCardProps> = ({
  text,
  subtitle,
  fontSize = 64,
  color = "#FFFFFF",
  backgroundColor = "#1F2937",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const opacity = spring({ frame, fps, config: { damping: 20 } });
  const scale = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 100 },
    from: 0.96,
    to: 1,
  });

  const titleSize = Math.max(
    58,
    Math.min(fontSize * 1.08, text.length > 90 ? 74 : text.length > 55 ? 84 : 108)
  );
  const subtitleSize = Math.max(28, Math.round(titleSize * 0.38));

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background: `radial-gradient(circle at 18% 20%, rgba(255,255,255,0.08), transparent 26%),
          radial-gradient(circle at 82% 18%, rgba(255,255,255,0.06), transparent 22%),
          linear-gradient(135deg, ${backgroundColor} 0%, #0f172a 100%)`,
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(120deg, rgba(255,255,255,0.04), transparent 35%, rgba(255,255,255,0.06) 62%, transparent 88%)",
        }}
      />
      <div
        style={{
          opacity,
          transform: `scale(${scale})`,
          width: "min(1500px, 84%)",
          padding: "72px 84px",
          borderRadius: 40,
          position: "relative",
          background:
            "linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.06))",
          border: "1px solid rgba(255,255,255,0.14)",
          boxShadow: "0 40px 100px rgba(2,6,23,0.36)",
          backdropFilter: "blur(14px)",
          color,
          textAlign: "left",
          fontFamily: "Manrope, Inter, system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 10,
            marginBottom: 28,
            padding: "10px 16px",
            borderRadius: 999,
            background: "rgba(255,255,255,0.08)",
            color: "rgba(255,255,255,0.74)",
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: "0.11em",
            textTransform: "uppercase",
          }}
        >
          Key message
        </div>
        <div
          style={{
            maxWidth: 1280,
            fontSize: titleSize,
            fontWeight: 900,
            lineHeight: 0.96,
            letterSpacing: "-0.05em",
            wordBreak: "break-word",
            overflowWrap: "anywhere",
            textShadow: "0 18px 45px rgba(2,6,23,0.3)",
          }}
        >
          {text}
        </div>
        {subtitle && (
          <div
            style={{
              marginTop: 28,
              maxWidth: 1120,
              fontSize: subtitleSize,
              fontWeight: 500,
              lineHeight: 1.45,
              color: "rgba(255,255,255,0.88)",
              wordBreak: "break-word",
              overflowWrap: "anywhere",
              opacity: spring({
                frame: frame - 8,
                fps,
                config: { damping: 20 },
              }),
            }}
          >
            {subtitle}
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
