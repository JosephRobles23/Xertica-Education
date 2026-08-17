"""Shared Xertica visual tokens for generated learning artifacts."""

XERTICA_BRAND = {
    "surface": "#fffef8",
    "cream": "#f2edd8",
    "ink": "#1a1814",
    "ink_soft": "#5c574f",
    "celeste": "#1899af",
    "magenta": "#c45baa",
    "verde": "#2e8b5a",
    "rojo": "#d9503b",
    "amarillo": "#faf338",
    "morado": "#5c3a8a",
    "marron": "#2a1a12",
    "naranja": "#e8651e",
}

XERTICA_PALETTE = ", ".join(f"{name} {value}" for name, value in XERTICA_BRAND.items())

XERTICA_IMAGE_STYLE = (
    "Usa el branding Xertica.ai: fondo marfil claro #fffef8, tinta negra #1a1814, "
    "tipografía grotesca pesada tipo Helvetica Neue/Inter, mucho espacio negativo y "
    "composición editorial geométrica modular. Usa bloques, rectángulos y triángulos "
    "planos con la paleta oficial (#1899af celeste, #c45baa magenta, #2e8b5a verde, "
    "#d9503b rojo, #faf338 amarillo, #5c3a8a morado, #2a1a12 marrón, #e8651e naranja). "
    "El color organiza jerarquías y conceptos, no se convierte en un degradado. "
    "Evita dark mode, glassmorphism, neón, sombras pesadas, fotografías y renders 3D realistas."
)
