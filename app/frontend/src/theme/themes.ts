import { theme as antdTheme, type ThemeConfig } from 'antd'

export type ThemeName = 'green' | 'turquoise' | 'blue' | 'dark' | 'onec'
export type ThemeChoice = ThemeName | 'auto' | ''
export type Density = 'normal' | 'compact'
/** Butoanele: plate (2D) sau în relief (3D) — alegerea fiecărui utilizator, în Profilul meu. */
export type ButtonStyle = '2d' | '3d'

interface Palette {
  primary: string
  primaryForText: string // nuanță mai închisă, pentru text alb pe buton (contrast WCAG AA)
  bg: string
  surface: string
  text: string
  siderBg: string
  siderText: string
  highlight: string
  dark: boolean
}

export const PALETTES: Record<ThemeName, Palette> = {
  green: {
    primary: '#1FA463',
    primaryForText: '#15834D',
    bg: '#F4FAF6',
    surface: '#FFFFFF',
    text: '#1C2B22',
    siderBg: '#F8FCF9',
    siderText: '#1C2B22',
    highlight: '#E6F5EC',
    dark: false,
  },
  // turcoazul adevărat, ca în celelalte programe CAI (bugetar, acoperiș)
  turquoise: {
    primary: '#07BCCB',
    primaryForText: '#0699A6',
    bg: '#F4FBFC',
    surface: '#FFFFFF',
    text: '#1E2A30',
    siderBg: '#FFFFFF',
    siderText: '#1E2A30',
    highlight: '#E6F8FA',
    dark: false,
  },
  blue: {
    primary: '#1E6FD9',
    primaryForText: '#1E6FD9',
    bg: '#F5F8FC',
    surface: '#FFFFFF',
    text: '#1B2533',
    siderBg: '#FFFFFF',
    siderText: '#1B2533',
    highlight: '#EAF2FD',
    dark: false,
  },
  // Ca în 1C: fundalul galben al formelor, tabelele albe cu linii, butoanele gri și butonul principal galben
  onec: {
    primary: '#D9A300',
    primaryForText: '#7A5B00',
    bg: '#F7EDC2',
    surface: '#FDF8E2',
    text: '#222222',
    siderBg: '#FBEFBF',
    siderText: '#222222',
    highlight: '#FBE08A',
    dark: false,
  },
  dark: {
    primary: '#3DDC84',
    primaryForText: '#16924F',
    bg: '#101813',
    surface: '#18231C',
    text: '#E3EFE7',
    siderBg: '#131D16',
    siderText: '#E3EFE7',
    highlight: '#1E3326',
    dark: true,
  },
}

// Culorile de status sunt aceleași în toate temele.
export const STATUS_COLORS = {
  success: '#2E9E5B', // aprobat / livrat
  warning: '#E0A100', // în lucru / așteaptă
  error: '#D64545', // refuzat / anulat / datorie
  neutral: '#8A97A0', // ciornă / închis
}

/** Varianta mai închisă a unei culori (pentru butoane cu text alb). */
export function darken(hex: string, amount = 0.18): string {
  const n = parseInt(hex.slice(1), 16)
  const f = (v: number) => Math.max(0, Math.round(v * (1 - amount)))
  const r = f((n >> 16) & 255)
  const g = f((n >> 8) & 255)
  const b = f(n & 255)
  return '#' + [r, g, b].map((v) => v.toString(16).padStart(2, '0')).join('')
}

/** Culoarea cu transparență (pentru umbre și inelul câmpului activ). */
export function alpha(hex: string, a: number): string {
  const n = parseInt(hex.slice(1), 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`
}

export function resolveTheme(choice: ThemeChoice, companyDefault: ThemeName, prefersDark: boolean): ThemeName {
  if (choice === 'auto') return prefersDark ? 'dark' : companyDefault === 'dark' ? 'green' : companyDefault
  if (choice && choice in PALETTES) return choice as ThemeName
  return companyDefault
}

/** Tema „Ca în 1C”: câmpuri și tabele albe cu chenar gri, colțuri aproape drepte, rânduri dese, scris Arial 13 px. */
function onecTheme(density: Density): ThemeConfig {
  const p = PALETTES.onec
  const algorithms = [antdTheme.defaultAlgorithm]
  if (density === 'compact') algorithms.push(antdTheme.compactAlgorithm)
  return {
    algorithm: algorithms,
    token: {
      colorPrimary: p.primary,
      colorInfo: '#3D6FB4',
      colorLink: '#1F5FA8',
      colorSuccess: STATUS_COLORS.success,
      colorWarning: STATUS_COLORS.warning,
      colorError: STATUS_COLORS.error,
      colorBgLayout: p.bg,
      colorBgContainer: p.surface,
      colorText: p.text,
      fontSize: 13,
      borderRadius: 3,
      borderRadiusLG: 4,
      borderRadiusSM: 2,
      controlHeight: density === 'compact' ? 26 : 28,
      colorBorder: '#A7A7A7',
      colorBorderSecondary: '#DDD3AA',
      controlOutline: alpha(p.primary, 0.3),
      controlOutlineWidth: 2,
      fontFamily: "Arial, 'Segoe UI', Tahoma, sans-serif",
    },
    components: {
      Layout: { siderBg: p.siderBg, headerBg: '#FFE57F', bodyBg: p.bg, triggerBg: p.siderBg, triggerColor: p.siderText },
      Menu: { itemBg: p.siderBg, itemSelectedBg: '#F7D34F', itemSelectedColor: '#222222', itemHoverBg: '#FCE8A0', horizontalItemSelectedColor: '#222222', itemHeight: 34 },
      Button: { fontWeight: 400, paddingInline: 12, primaryShadow: 'none', defaultShadow: 'none', dangerShadow: 'none',
        colorPrimary: '#F5CF3D', colorPrimaryHover: '#F9DC62', colorPrimaryActive: '#E8BE22', primaryColor: '#222222',
        defaultBorderColor: '#9C9C9C', defaultColor: '#222222', defaultBg: '#F4F4F4', defaultHoverBorderColor: '#7A7A7A', defaultHoverColor: '#000000',
        defaultHoverBg: '#FFFFFF' },
      Input: { colorBgContainer: '#FFFFFF', activeShadow: `0 0 0 2px ${alpha(p.primary, 0.3)}`, hoverBorderColor: '#7A7A7A', paddingInline: 6 },
      InputNumber: { colorBgContainer: '#FFFFFF', activeShadow: `0 0 0 2px ${alpha(p.primary, 0.3)}`, hoverBorderColor: '#7A7A7A' },
      Select: { colorBgContainer: '#FFFFFF', activeOutlineColor: alpha(p.primary, 0.3), hoverBorderColor: '#7A7A7A', optionSelectedBg: '#FBE08A', optionActiveBg: '#FFF4CC' },
      DatePicker: { colorBgContainer: '#FFFFFF', activeShadow: `0 0 0 2px ${alpha(p.primary, 0.3)}`, hoverBorderColor: '#7A7A7A' },
      Card: { headerFontSize: 14, headerBg: '#FBEBB0', colorBorderSecondary: '#D9CB8C' },
      Tabs: { itemSelectedColor: '#222222', inkBarColor: '#D9A300', titleFontSize: 13, itemHoverColor: '#000000', cardBg: '#F3E6AE' },
      Table: { colorBgContainer: '#FFFFFF', headerBg: '#EFECE0', headerColor: '#222222', rowHoverBg: '#FFF6D2', rowSelectedBg: '#FCE7A0',
        rowSelectedHoverBg: '#FADD7C', borderColor: '#D9D5C3', footerBg: '#F7F3E4', headerSplitColor: '#C9C4AE', cellPaddingBlockSM: 3, cellPaddingInlineSM: 6 },
      Modal: { headerBg: '#FBEBB0', contentBg: '#FDF8E2', titleFontSize: 14 },
      Descriptions: { labelBg: '#F5EFD5' },
      Segmented: { itemSelectedBg: '#F5CF3D', trackBg: '#EDE3BC' },
      Checkbox: { colorPrimary: '#D9A300' },
      Tag: { defaultBg: '#F5F2E6' },
    },
  }
}

export function buildTheme(name: ThemeName, density: Density, customPrimary?: string, buttons: ButtonStyle = '3d'): ThemeConfig {
  if (name === 'onec') return onecTheme(density)
  const p = PALETTES[name]
  // Culoarea proprie a firmei (din Constante) înlocuiește culoarea principală în temele luminoase.
  const primary = customPrimary && !p.dark ? customPrimary : p.primary
  const buttonPrimary = customPrimary && !p.dark ? darken(customPrimary, 0.12) : p.primaryForText
  const flat = buttons === '2d'
  const algorithms = [p.dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm]
  if (density === 'compact') algorithms.push(antdTheme.compactAlgorithm)
  return {
    algorithm: algorithms,
    token: {
      colorPrimary: primary,
      colorInfo: primary,
      colorSuccess: STATUS_COLORS.success,
      colorWarning: STATUS_COLORS.warning,
      colorError: STATUS_COLORS.error,
      colorBgLayout: p.bg,
      colorBgContainer: p.surface,
      colorText: p.text,
      // designul „Vânzări”: colțuri mai rotunde, carduri mai moi
      borderRadius: 12,
      borderRadiusLG: 16,
      borderRadiusSM: 8,
      controlHeight: density === 'compact' ? 32 : 36,
      colorBorder: p.dark ? '#33493B' : '#BCCFC3',
      colorBorderSecondary: p.dark ? '#24362A' : '#E1ECE5',
      controlOutline: alpha(primary, 0.25),
      controlOutlineWidth: 3,
      fontFamily:
        "Inter, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, 'Noto Sans', sans-serif",
    },
    components: {
      Layout: { siderBg: p.siderBg, headerBg: p.surface, bodyBg: p.bg, triggerBg: p.siderBg, triggerColor: p.siderText },
      Menu: {
        itemBg: p.siderBg,
        itemSelectedBg: p.highlight,
        itemSelectedColor: p.dark ? p.primary : darken(primary, 0.25),
      },
      Button: {
        colorPrimary: buttonPrimary, colorPrimaryHover: primary, fontWeight: 600, paddingInline: 18,
        // 3D: umbra de sub buton; relieful (lumina de sus, muchia de jos) vine din styles.css, după html[data-buttons]
        primaryShadow: flat ? 'none' : `0 3px 8px ${alpha(buttonPrimary, 0.35)}`,
        defaultShadow: flat || p.dark ? 'none' : '0 1px 3px rgba(20, 40, 50, 0.10)',
        dangerShadow: flat ? 'none' : `0 3px 8px ${alpha(STATUS_COLORS.error, 0.3)}`,
        defaultBorderColor: p.dark ? '#33493B' : '#AFC6B7',
        defaultColor: p.dark ? p.text : darken(primary, 0.35),
        defaultHoverBorderColor: primary, defaultHoverColor: darken(primary, 0.15),
      },
      Input: { activeShadow: `0 0 0 3px ${alpha(primary, 0.22)}`, hoverBorderColor: primary, paddingInline: 12 },
      InputNumber: { activeShadow: `0 0 0 3px ${alpha(primary, 0.22)}`, hoverBorderColor: primary },
      Select: { activeOutlineColor: alpha(primary, 0.22), hoverBorderColor: primary, optionSelectedBg: p.highlight },
      DatePicker: { activeShadow: `0 0 0 3px ${alpha(primary, 0.22)}`, hoverBorderColor: primary },
      Card: { headerFontSize: 15 },
      Tabs: { itemSelectedColor: p.dark ? p.primary : darken(primary, 0.2), inkBarColor: primary, titleFontSize: 14 },
      Table: { headerBg: p.dark ? '#1C2A21' : p.highlight, headerColor: p.text, rowHoverBg: p.highlight, headerBorderRadius: 12 },
    },
  }
}
