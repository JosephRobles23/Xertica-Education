import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

type CalloutType = "info" | "warning" | "tip" | "quote";

interface CalloutBoxProps {
  text: string;
  type?: CalloutType;
  icon?: string;
  title?: string;
  borderColor?: string;
  backgroundColor?: string;
  textColor?: string;
  fontFamily?: string;
  fontSize?: number;
  titleFontSize?: number;
  containerBackgroundColor?: string;
}

const TYPE_DEFAULTS: Record<
  CalloutType,
  { badge: string; border: string; panel: string; glow: string; symbol: string }
> = {
  info: {
    badge: "Insight",
    border: "#2563EB",
    panel: "linear-gradient(180deg, rgba(239,246,255,0.98) 0%, rgba(219,234,254,0.94) 100%)",
    glow: "rgba(37,99,235,0.16)",
    symbol: "i",
  },
  warning: {
    badge: "Atencion",
    border: "#D97706",
    panel: "linear-gradient(180deg, rgba(255,251,235,0.98) 0%, rgba(254,243,199,0.94) 100%)",
    glow: "rgba(217,119,6,0.16)",
    symbol: "!",
  },
  tip: {
    badge: "Clave",
    border: "#0F766E",
    panel: "linear-gradient(180deg, rgba(240,253,250,0.98) 0%, rgba(204,251,241,0.94) 100%)",
    glow: "rgba(15,118,110,0.15)",
    symbol: "+",
  },
  quote: {
    badge: "Cita",
    border: "#475569",
    panel: "linear-gradient(180deg, rgba(248,250,252,0.98) 0%, rgba(241,245,249,0.94) 100%)",
    glow: "rgba(71,85,105,0.14)",
    symbol: "\"",
  },
};

const bodySizeForText = (text: string, fallback: number) => {
  const length = text.trim().length;
  if (fallback !== 32) return fallback;
  if (length > 180) return 38;
  if (length > 120) return 42;
  return 48;
};

export const CalloutBox: React.FC<CalloutBoxProps> = ({
  text,
  type = "info",
  icon,
  title,
  borderColor,
  backgroundColor,
  textColor = "#0F172A",
  fontFamily = '"Avenir Next", "Helvetica Neue", "Segoe UI", sans-serif',
  fontSize = 32,
  titleFontSize = 24,
  containerBackgroundColor = "#F8FAFC",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const defaults = TYPE_DEFAULTS[type];
  const resolvedBorder = borderColor || defaults.border;
  const resolvedBg = backgroundColor || defaults.panel;
  const resolvedIcon = icon || defaults.symbol;
  const resolvedTitle = title || defaults.badge;
  const resolvedBodySize = bodySizeForText(text, fontSize);

  const shell = spring({ frame, fps, config: { damping: 18 } });
  const shellLift = interpolate(shell, [0, 1], [30, 0]);
  const shellScale = interpolate(shell, [0, 1], [0.96, 1]);
  const accentHeight = interpolate(
    spring({ frame: frame - 6, fps, config: { damping: 16, stiffness: 90 } }),
    [0, 1],
    [0, 100]
  );

  return (
    <AbsoluteFill
      style={{
        display: "flex",
        background: `radial-gradient(circle at 84% 16%, ${defaults.glow}, transparent 22%), ${containerBackgroundColor}`,
        justifyContent: "center",
        alignItems: "center",
        padding: "72px 92px",
      }}
    >
      <div
        style={{
          width: "82%",
          maxWidth: 1500,
          position: "relative",
          opacity: shell,
          transform: `translateY(${shellLift}px) scale(${shellScale})`,
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 10,
            borderRadius: 999,
            background: resolvedBorder,
            height: `${accentHeight}%`,
            boxShadow: `0 0 28px ${defaults.glow}`,
          }}
        />

        <div
          style={{
            marginLeft: 22,
            borderRadius: 34,
            padding: "52px 58px 56px",
            background: resolvedBg,
            border: "1px solid rgba(148, 163, 184, 0.16)",
            boxShadow: "0 34px 84px rgba(15, 23, 42, 0.10)",
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 20,
            }}
          >
            <div
              style={{
                width: 74,
                height: 74,
                borderRadius: 999,
                background: "rgba(255,255,255,0.68)",
                border: `2px solid ${resolvedBorder}`,
                color: resolvedBorder,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                fontFamily: type === "quote" ? '"Iowan Old Style", Georgia, serif' : fontFamily,
                fontSize: type === "quote" ? 44 : 34,
                fontWeight: 700,
                boxShadow: `0 12px 32px ${defaults.glow}`,
              }}
            >
              {resolvedIcon}
            </div>

            <div
              style={{
                fontFamily,
                fontWeight: 800,
                fontSize: titleFontSize,
                lineHeight: 1,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: resolvedBorder,
              }}
            >
              {resolvedTitle}
            </div>
          </div>

          <div
            style={{
              marginTop: 28,
              maxWidth: "94%",
              fontFamily: type === "quote" ? '"Iowan Old Style", Georgia, serif' : fontFamily,
              fontStyle: type === "quote" ? "italic" : "normal",
              fontWeight: type === "quote" ? 500 : 600,
              fontSize: resolvedBodySize,
              color: textColor,
              lineHeight: 1.34,
              letterSpacing: "-0.02em",
            }}
          >
            {text}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
