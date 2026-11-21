import { theme as antdTheme, type ThemeConfig } from 'antd'

export type ThemeName = 'desktop' | 'desktop_dark' | 'green' | 'turquoise' | 'blue' | 'dark' | 'onec'
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
  /** aspectul programului: „desktop” — program clasic de birou (bara de titlu, meniul, bara de unelte, bara de stare,
   *  ferestrele ca file); altfel — meniul lateral, ca până acum */
  look?: 'desktop'
}

export const PALETTES: Record<ThemeName, Palette> = {
  // Program clasic de birou (implicit): ferestre gri deschis, câmpuri și tabele albe cu chenar subțire, selecția albastră
  desktop: {
    primary: '#0067C0',
    primaryForText: '#0067C0',
    bg: '#E9E9E9',
    surface: '#F0F0F0',
    text: '#1A1A1A',
    siderBg: '#F0F0F0',
    siderText: '#1A1A1A',
    highlight: '#CCE8FF',
    dark: false,
    look: 'desktop',
  },
  desktop_dark: {
    primary: '#4CA3F0',
    primaryForText: '#1F6FB8',
    bg: '#1E1E1E',
    surface: '#2B2B2B',
    text: '#E8E8E8',
    siderBg: '#2B2B2B',
    siderText: '#E8E8E8',
    highlight: '#264F78',
    dark: true,
    look: 'desktop',
  },
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

/** Tema implicită când întreprinderea n-a ales alta (și înainte să vină datele ei de la server). */
export const DEFAULT_THEME: ThemeName = 'desktop'

/** Tema are aspectul de program clasic de birou (layout/DesktopLayout). */
export const isDesktopLook = (name: ThemeName) => PALETTES[name]?.look === 'desktop'

/** Tema aleasă → tema folosită. „Automat” urmează sistemul: întunecată noaptea, cea a întreprinderii ziua — în aspectul
 *  clasic de birou varianta lui întunecată / luminoasă, ca aspectul să nu se schimbe odată cu culorile. */
export function resolveTheme(choice: ThemeChoice, companyDefault: ThemeName, prefersDark: boolean): ThemeName {
  const company = companyDefault in PALETTES ? companyDefault : DEFAULT_THEME
  if (choice === 'auto') {
    if (isDesktopLook(company)) return prefersDark ? 'desktop_dark' : 'desktop'
    return prefersDark ? 'dark' : company === 'dark' ? 'green' : company
  }
  if (choice && choice in PALETTES) return choice as ThemeName
  return company
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

/**
 * Tema „Clasic de birou”: aspectul unui program de birou (Windows / Qt) — scrisul sistemului de 12–13 px, rânduri dese,
 * colțuri drepte, fără umbre mari și fără animații, ferestrele și panourile gri deschis, câmpurile și tabelele albe cu
 * chenar de 1 px, rândul ales albastru deschis. Restul (bara de titlu, chenarele grupelor, dialogurile cu bară de titlu,
 * butoanele în relief discret) vine din styles.css, după html[data-look='desktop'].
 */
function desktopTheme(dark: boolean, density: Density): ThemeConfig {
  const p = PALETTES[dark ? 'desktop_dark' : 'desktop']
  const compact = density === 'compact'
  const c = dark
    ? { field: '#1E1E1E', border: '#5C5C5C', borderSoft: '#3D3D3D', hover: '#2A3A4A', selected: '#264F78', selectedHover: '#2D5C8A',
      header: '#333333', grid: '#3A3A3A', menuHover: '#3A4A5A', link: '#6CB4F5', textSoft: '#B5B5B5' }
    : { field: '#FFFFFF', border: '#ABADB3', borderSoft: '#D5D5D5', hover: '#E5F3FF', selected: '#CCE8FF', selectedHover: '#B8DEFF',
      header: '#F3F3F3', grid: '#E2E2E2', menuHover: '#CCE8FF', link: '#0066CC', textSoft: '#5A5A5A' }
  const algorithms = [dark ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm]
  return {
    algorithm: algorithms,
    token: {
      colorPrimary: p.primary,
      colorInfo: p.primary,
      colorLink: c.link,
      colorSuccess: STATUS_COLORS.success,
      colorWarning: STATUS_COLORS.warning,
      colorError: STATUS_COLORS.error,
      colorBgLayout: p.bg,
      colorBgContainer: c.field,
      colorBgElevated: p.surface,
      colorText: p.text,
      colorTextSecondary: c.textSoft,
      colorBorder: c.border,
      colorBorderSecondary: c.borderSoft,
      colorSplit: c.borderSoft,
      fontFamily: "'Segoe UI', system-ui, -apple-system, 'Noto Sans', Tahoma, Arial, sans-serif",
      fontSize: compact ? 12 : 13,
      fontSizeSM: 12,
      fontSizeLG: compact ? 13 : 14,
      fontSizeHeading1: 20,
      fontSizeHeading2: 18,
      fontSizeHeading3: 16,
      fontSizeHeading4: 14,
      fontSizeHeading5: 13,
      lineHeight: 1.45,
      borderRadius: 0,
      borderRadiusLG: 0,
      borderRadiusSM: 0,
      borderRadiusXS: 0,
      borderRadiusOuter: 0,
      controlHeight: compact ? 22 : 24,
      controlHeightSM: compact ? 18 : 20,
      controlHeightLG: compact ? 26 : 28,
      controlOutline: 'transparent',
      controlOutlineWidth: 0,
      controlItemBgActive: c.selected,
      controlItemBgActiveHover: c.selectedHover,
      controlItemBgHover: c.hover,
      padding: 12,
      paddingLG: 16,
      paddingMD: 14,
      paddingSM: 8,
      paddingXS: 6,
      margin: 12,
      marginLG: 16,
      boxShadow: '2px 2px 6px rgba(0, 0, 0, 0.28)',
      boxShadowSecondary: '2px 2px 4px rgba(0, 0, 0, 0.28)',
      boxShadowTertiary: 'none',
      motion: false,
      wireframe: true,
    },
    components: {
      Layout: { siderBg: p.siderBg, headerBg: p.surface, bodyBg: p.bg, triggerBg: p.siderBg, triggerColor: p.siderText },
      Menu: { itemBg: 'transparent', itemSelectedBg: c.selected, itemSelectedColor: p.text, itemHoverBg: c.hover, itemHeight: 26,
        itemMarginBlock: 0, itemMarginInline: 0, itemBorderRadius: 0, subMenuItemBorderRadius: 0, activeBarBorderWidth: 0 },
      Button: { fontWeight: 400, paddingInline: 10, paddingInlineSM: 6, primaryShadow: 'none', defaultShadow: 'none', dangerShadow: 'none',
        defaultBg: dark ? '#3A3A3A' : '#E8E8E8', defaultBorderColor: dark ? '#6A6A6A' : '#ADADAD', defaultColor: p.text,
        defaultHoverBg: dark ? '#43505C' : '#E5F1FB', defaultHoverBorderColor: '#3C7FB1', defaultHoverColor: p.text,
        defaultActiveBg: dark ? '#2F4A63' : '#CCE4F7', defaultActiveBorderColor: '#2C628B', defaultActiveColor: p.text,
        primaryColor: p.text },
      Input: { colorBgContainer: c.field, activeShadow: 'none', hoverBorderColor: '#7EB4EA', activeBorderColor: '#3399FF', paddingInline: 4,
        paddingInlineSM: 3 },
      InputNumber: { colorBgContainer: c.field, activeShadow: 'none', hoverBorderColor: '#7EB4EA', activeBorderColor: '#3399FF', paddingInline: 4 },
      Select: { colorBgContainer: c.field, activeOutlineColor: 'transparent', hoverBorderColor: '#7EB4EA', activeBorderColor: '#3399FF',
        optionSelectedBg: c.selected, optionActiveBg: c.hover, optionHeight: 22, optionPadding: '2px 6px', optionSelectedFontWeight: 400 },
      DatePicker: { colorBgContainer: c.field, activeShadow: 'none', hoverBorderColor: '#7EB4EA', activeBorderColor: '#3399FF' },
      Checkbox: { borderRadiusSM: 0 },
      Radio: { buttonSolidCheckedBg: p.primary, dotSize: 6, radioSize: 13 },
      Card: { headerFontSize: 13, headerFontSizeSM: 12, headerHeight: 30, headerHeightSM: 26, headerPadding: 8, bodyPadding: 10,
        bodyPaddingSM: 8, colorBgContainer: p.surface, headerBg: dark ? '#333333' : '#F7F7F7', extraColor: p.text },
      Tabs: { cardBg: dark ? '#262626' : '#E3E3E3', cardHeight: 26, cardPadding: '3px 10px', cardGutter: 2, horizontalMargin: '0 0 8px 0',
        horizontalItemPadding: '4px 10px', horizontalItemGutter: 2, titleFontSize: compact ? 12 : 13, itemSelectedColor: p.text,
        itemHoverColor: p.text, inkBarColor: 'transparent', itemColor: p.text },
      Table: { colorBgContainer: c.field, headerBg: c.header, headerColor: p.text, headerSplitColor: c.borderSoft, rowHoverBg: c.hover,
        rowSelectedBg: c.selected, rowSelectedHoverBg: c.selectedHover, borderColor: c.grid, footerBg: c.header,
        cellPaddingBlock: 3, cellPaddingInline: 6, cellPaddingBlockMD: 3, cellPaddingInlineMD: 6, cellPaddingBlockSM: 2,
        cellPaddingInlineSM: 5, headerBorderRadius: 0, cellFontSize: compact ? 12 : 13, cellFontSizeSM: compact ? 12 : 13,
        cellFontSizeMD: compact ? 12 : 13, selectionColumnWidth: 28, expandIconBg: c.field },
      // paddingul antetului / corpului / subsolului (bara de titlu a dialogului) — din `wireframe` și din styles.css
      Modal: { titleFontSize: 12, titleLineHeight: 1.6, contentBg: p.surface, headerBg: dark ? '#3A3A3A' : '#DDE6F0' },
      Drawer: { footerPaddingBlock: 6, footerPaddingInline: 12 },
      Descriptions: { labelBg: c.header, itemPaddingBottom: 4, titleMarginBottom: 6 },
      Collapse: { headerBg: c.header, headerPadding: '4px 8px', contentPadding: '8px 10px', contentBg: p.surface },
      Segmented: { itemSelectedBg: c.field, trackBg: dark ? '#3A3A3A' : '#DADADA', trackPadding: 1 },
      Tag: { defaultBg: c.header },
      Dropdown: { paddingBlock: 3, controlPaddingHorizontal: 10 },
      Tooltip: { colorBgSpotlight: dark ? '#3A3A3A' : '#FFFFE1', colorTextLightSolid: p.text, borderRadius: 0 },
      Form: { itemMarginBottom: 8, verticalLabelPadding: '0 0 2px', labelFontSize: compact ? 12 : 13 },
      List: { itemPadding: '4px 6px', itemPaddingSM: '3px 6px' },
      Pagination: { itemSize: 22, itemSizeSM: 20 },
      Alert: { defaultPadding: '6px 10px', withDescriptionPadding: '8px 12px' },
      Badge: { indicatorHeight: 16, indicatorHeightSM: 14 },
    },
  }
}

export function buildTheme(name: ThemeName, density: Density, customPrimary?: string, buttons: ButtonStyle = '3d'): ThemeConfig {
  if (isDesktopLook(name)) return desktopTheme(PALETTES[name].dark, density)
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
