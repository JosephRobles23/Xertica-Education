import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

interface HeroTitleProps {
  title: string;
  subtitle?: string;
}

export const HeroTitle: React.FC<HeroTitleProps> = ({ title, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const words = title.trim().split(/\s+/).filter(Boolean);
  const titleSize = Math.max(72, Math.min(136, 180 - title.length * 1));
  const subtitleSize = Math.max(24, Math.min(38, Math.round(titleSize * 0.24)));

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        background:
          "radial-gradient(circle at 18% 20%, rgba(56,189,248,0.22) 0%, transparent 28%)," +
          "radial-gradient(circle at 84% 18%, rgba(52,211,153,0.16) 0%, transparent 22%)," +
          "linear-gradient(135deg, #0b1020 0%, #111827 48%, #020617 100%)",
        overflow: "hidden",
      }}
    >
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "linear-gradient(110deg, rgba(255,255,255,0.04), transparent 30%, rgba(255,255,255,0.06) 68%, transparent 90%)",
        }}
      />
      <div
        style={{
          width: "min(1520px, 84%)",
          textAlign: "left",
          position: "relative",
          fontFamily: "Manrope, Inter, system-ui, sans-serif",
        }}
      >
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 12,
            padding: "11px 16px",
            borderRadius: 999,
            background: "rgba(255,255,255,0.08)",
            color: "rgba(255,255,255,0.84)",
            fontSize: 20,
            fontWeight: 800,
            letterSpacing: "0.12em",
            textTransform: "uppercase",
            marginBottom: 24,
            boxShadow: "0 8px 30px rgba(0,0,0,0.18)",
          }}
        >
          Video storyboard
        </div>
        <div
          style={{
            fontSize: titleSize,
            fontWeight: 900,
            lineHeight: 0.95,
            display: "flex",
            flexWrap: "wrap",
            gap: "0.24em 0.28em",
            maxWidth: 1360,
            letterSpacing: "-0.05em",
            color: "#F8FAFC",
          }}
        >
          {words.map((word, i) => {
            const wordSpring = spring({
              frame: frame - i * 5,
              fps,
              config: { damping: 14, stiffness: 110 },
            });

            return (
              <span
                key={`${word}-${i}`}
                style={{
                  display: "inline-flex",
                  opacity: wordSpring,
                  transform: `translateY(${interpolate(
                    wordSpring,
                    [0, 1],
                    [28, 0]
                  )}px)`,
                  color:
                    i === 0
                      ? "#38BDF8"
                      : i === words.length - 1
                        ? "#34D399"
                        : "#F8FAFC",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>
        {subtitle && (
          <div
            style={{
              marginTop: 26,
              opacity: spring({
                frame: frame - words.length * 5 - 5,
                fps,
                config: { damping: 18 },
              }),
              display: "inline-flex",
              alignItems: "center",
              padding: "12px 16px",
              borderRadius: 16,
              background: "rgba(255,255,255,0.08)",
              backdropFilter: "blur(10px)",
              fontSize: subtitleSize,
              fontWeight: 800,
              color: "rgba(255,255,255,0.92)",
              letterSpacing: "0.08em",
              textTransform: "uppercase",
            }}
          >
            {subtitle}
          </div>
        )}
        <div
          style={{
            marginTop: 34,
            width: interpolate(
              spring({
                frame: frame - 18,
                fps,
                config: { damping: 15, stiffness: 80 },
              }),
              [0, 1],
              [0, Math.min(820, 18 * Math.max(8, title.length))],
            ),
            height: 4,
            borderRadius: 999,
            background:
              "linear-gradient(90deg, rgba(56,189,248,0.2), rgba(56,189,248,1) 50%, rgba(52,211,153,1))",
            boxShadow: "0 0 30px rgba(56,189,248,0.25)",
          }}
        />
      </div>
    </AbsoluteFill>
  );
};
