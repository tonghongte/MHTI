import { computed, watchEffect } from 'vue'
import { useThemeStore } from '@/stores/theme'
import { darkTheme, type GlobalTheme, type GlobalThemeOverrides } from 'naive-ui'

/**
 * iOS 风格设计令牌
 * 与 ios-theme.css 中的 CSS 变量保持同步
 */

// iOS 风格品牌色定义
const iosColors = {
  // 主色调
  primary: '#007AFF',        // iOS 蓝
  primaryHover: '#0066D6',
  primaryPressed: '#0055B3',
  primarySuppl: '#409EFF',

  // 语义色
  success: '#34C759',        // iOS 绿
  successHover: '#2DB84D',
  warning: '#FF9500',        // iOS 橙
  warningHover: '#E68600',
  error: '#FF3B30',          // iOS 红
  errorHover: '#E6342B',
  info: '#5AC8FA',           // iOS 浅蓝
  infoHover: '#4AB8E8',

  // 中性色
  textPrimary: '#1C1C1E',
  textSecondary: '#8E8E93',
  textTertiary: '#C7C7CC',
  fill: '#F2F2F7',
  fillSecondary: '#E5E5EA',
}

// 圆角系统
const borderRadius = {
  xs: '4px',
  sm: '8px',
  md: '12px',
  lg: '16px',
  xl: '20px',
  full: '9999px',
}

// 阴影系统
const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.04)',
  md: '0 2px 8px rgba(0, 0, 0, 0.08)',
  lg: '0 4px 16px rgba(0, 0, 0, 0.12)',
  xl: '0 8px 32px rgba(0, 0, 0, 0.16)',
}

// 暗色模式阴影
const shadowsDark = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.2)',
  md: '0 2px 8px rgba(0, 0, 0, 0.3)',
  lg: '0 4px 16px rgba(0, 0, 0, 0.4)',
  xl: '0 8px 32px rgba(0, 0, 0, 0.5)',
}

// iOS 风格亮色主题覆盖
const lightThemeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: iosColors.primary,
    primaryColorHover: iosColors.primaryHover,
    primaryColorPressed: iosColors.primaryPressed,
    primaryColorSuppl: iosColors.primarySuppl,
    successColor: iosColors.success,
    successColorHover: iosColors.successHover,
    warningColor: iosColors.warning,
    warningColorHover: iosColors.warningHover,
    errorColor: iosColors.error,
    errorColorHover: iosColors.errorHover,
    infoColor: iosColors.info,
    infoColorHover: iosColors.infoHover,
    textColorBase: iosColors.textPrimary,
    textColor1: iosColors.textPrimary,
    textColor2: iosColors.textSecondary,
    textColor3: iosColors.textTertiary,
    borderRadius: borderRadius.md,
    borderRadiusSmall: borderRadius.sm,
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", "PingFang SC", sans-serif',
    fontFamilyMono: '"SF Mono", "Menlo", "Monaco", "Consolas", monospace',
    fontSize: '15px',
    fontSizeMini: '12px',
    fontSizeTiny: '13px',
    fontSizeSmall: '14px',
    fontSizeMedium: '15px',
    fontSizeLarge: '16px',
    fontSizeHuge: '18px',
    lineHeight: '1.5',
    bodyColor: iosColors.fill,
    cardColor: '#FFFFFF',
    modalColor: '#FFFFFF',
    popoverColor: '#FFFFFF',
    hoverColor: 'rgba(0, 122, 255, 0.08)',
    borderColor: 'rgba(60, 60, 67, 0.12)',
    dividerColor: 'rgba(60, 60, 67, 0.12)',
    heightTiny: '28px',
    heightSmall: '36px',
    heightMedium: '44px',  // iOS 推荐触摸目标
    heightLarge: '52px',
    heightHuge: '60px',
  },
  Card: {
    borderRadius: borderRadius.lg,
    paddingSmall: '12px',
    paddingMedium: '16px',
    paddingLarge: '20px',
    paddingHuge: '24px',
    boxShadow: shadows.md,
  },
  Button: {
    borderRadiusTiny: borderRadius.xs,
    borderRadiusSmall: borderRadius.sm,
    borderRadiusMedium: borderRadius.md,
    borderRadiusLarge: borderRadius.md,
    heightTiny: '28px',
    heightSmall: '36px',
    heightMedium: '44px',
    heightLarge: '52px',
    fontSizeTiny: '13px',
    fontSizeSmall: '14px',
    fontSizeMedium: '16px',
    fontSizeLarge: '17px',
    fontWeight: '500',
    fontWeightStrong: '600',
    paddingTiny: '0 10px',
    paddingSmall: '0 14px',
    paddingMedium: '0 20px',
    paddingLarge: '0 24px',
  },
  Menu: {
    borderRadius: borderRadius.md,
    itemHeight: '44px',
    itemColorActive: 'rgba(0, 122, 255, 0.1)',
    itemColorActiveHover: 'rgba(0, 122, 255, 0.15)',
    itemTextColorActive: iosColors.primary,
    itemTextColorActiveHover: iosColors.primary,
    itemIconColorActive: iosColors.primary,
    itemIconColorActiveHover: iosColors.primary,
    itemTextColorHover: iosColors.primary,
    itemIconColorHover: iosColors.primary,
  },
  DataTable: {
    borderRadius: borderRadius.md,
    thPaddingSmall: '8px 12px',
    thPaddingMedium: '12px 16px',
    thPaddingLarge: '16px 20px',
    tdPaddingSmall: '8px 12px',
    tdPaddingMedium: '12px 16px',
    tdPaddingLarge: '16px 20px',
  },
  Tag: {
    borderRadius: borderRadius.sm,
    heightSmall: '22px',
    heightMedium: '26px',
    heightLarge: '32px',
    fontSizeSmall: '12px',
    fontSizeMedium: '13px',
    fontSizeLarge: '14px',
  },
  Input: {
    borderRadius: borderRadius.md,
    heightTiny: '28px',
    heightSmall: '36px',
    heightMedium: '44px',
    heightLarge: '52px',
    fontSizeTiny: '13px',
    fontSizeSmall: '14px',
    fontSizeMedium: '15px',
    fontSizeLarge: '16px',
    paddingTiny: '0 8px',
    paddingSmall: '0 10px',
    paddingMedium: '0 12px',
    paddingLarge: '0 14px',
  },
  Select: {
    peers: {
      InternalSelection: {
        borderRadius: borderRadius.md,
        heightTiny: '28px',
        heightSmall: '36px',
        heightMedium: '44px',
        heightLarge: '52px',
      },
    },
  },
  Tabs: {
    tabBorderRadius: borderRadius.sm,
    tabPaddingSmallSegment: '6px 12px',
    tabPaddingMediumSegment: '8px 16px',
    tabPaddingLargeSegment: '10px 20px',
  },
  Message: {
    borderRadius: borderRadius.md,
    padding: '12px 16px',
    iconMargin: '0 10px 0 0',
    maxWidth: '400px',
  },
  Notification: {
    borderRadius: borderRadius.lg,
    padding: '16px',
    boxShadow: shadows.lg,
  },
  Dialog: {
    borderRadius: borderRadius.lg,
    padding: '24px',
    titleFontSize: '17px',
    fontSize: '15px',
  },
  Drawer: {
    borderRadius: '16px 0 0 16px',
    headerPadding: '16px 20px',
    bodyPadding: '16px 20px',
    footerPadding: '16px 20px',
  },
  Modal: {
    borderRadius: borderRadius.lg,
    boxShadow: shadows.xl,
  },
  Tooltip: {
    borderRadius: borderRadius.sm,
    padding: '8px 12px',
  },
  Popover: {
    borderRadius: borderRadius.md,
    padding: '12px 16px',
    boxShadow: shadows.lg,
  },
  Progress: {
    railHeight: '6px',
    fontSizeCircle: '24px',
    fontWeightCircle: '600',
  },
  Switch: {
    railHeightSmall: '22px',
    railHeightMedium: '26px',
    railHeightLarge: '30px',
    railWidthSmall: '40px',
    railWidthMedium: '48px',
    railWidthLarge: '56px',
    buttonHeightSmall: '18px',
    buttonHeightMedium: '22px',
    buttonHeightLarge: '26px',
    buttonWidthSmall: '18px',
    buttonWidthMedium: '22px',
    buttonWidthLarge: '26px',
    railColor: 'rgba(120, 120, 128, 0.16)',
    railColorActive: iosColors.success,  // iOS 开关使用绿色
  },
  Slider: {
    railHeight: '4px',
    handleSize: '24px',
    fillColor: iosColors.primary,
    fillColorHover: iosColors.primaryHover,
  },
  Avatar: {
    borderRadius: borderRadius.full,
  },
  Badge: {
    fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", sans-serif',
    fontSize: '12px',
  },
  Collapse: {
    titlePadding: '16px 0',
    dividerColor: 'rgba(60, 60, 67, 0.12)',
  },
  List: {
    borderRadius: borderRadius.md,
  },
  Form: {
    labelFontSizeTopSmall: '13px',
    labelFontSizeTopMedium: '14px',
    labelFontSizeTopLarge: '15px',
    labelFontSizeLeftSmall: '14px',
    labelFontSizeLeftMedium: '15px',
    labelFontSizeLeftLarge: '16px',
    feedbackFontSizeMedium: '13px',
    feedbackHeightMedium: '22px',
  },
  Skeleton: {
    borderRadius: borderRadius.sm,
  },
}

// iOS 风格暗色主题覆盖
const darkThemeOverrides: GlobalThemeOverrides = {
  common: {
    ...lightThemeOverrides.common,
    textColorBase: '#FFFFFF',
    textColor1: '#FFFFFF',
    textColor2: '#EBEBF5',
    textColor3: '#EBEBF599',
    bodyColor: '#000000',
    cardColor: '#1C1C1E',
    modalColor: '#1C1C1E',
    popoverColor: '#2C2C2E',
    tableColor: '#1C1C1E',
    inputColor: '#2C2C2E',
    actionColor: '#2C2C2E',
    hoverColor: 'rgba(0, 122, 255, 0.15)',
    borderColor: 'rgba(84, 84, 88, 0.65)',
    dividerColor: 'rgba(84, 84, 88, 0.65)',
  },
  Card: {
    ...lightThemeOverrides.Card,
    color: '#1C1C1E',
    boxShadow: shadowsDark.md,
  },
  Menu: {
    ...lightThemeOverrides.Menu,
    itemColorActive: 'rgba(0, 122, 255, 0.2)',
    itemColorActiveHover: 'rgba(0, 122, 255, 0.25)',
    color: '#1C1C1E',
  },
  Layout: {
    siderColor: '#1C1C1E',
    siderBorderColor: 'rgba(84, 84, 88, 0.65)',
    headerColor: '#1C1C1E',
    headerBorderColor: 'rgba(84, 84, 88, 0.65)',
  },
  DataTable: {
    ...lightThemeOverrides.DataTable,
    thColor: '#2C2C2E',
    tdColor: '#1C1C1E',
    tdColorHover: '#2C2C2E',
  },
  Notification: {
    ...lightThemeOverrides.Notification,
    boxShadow: shadowsDark.lg,
  },
  Modal: {
    ...lightThemeOverrides.Modal,
    boxShadow: shadowsDark.xl,
  },
  Popover: {
    ...lightThemeOverrides.Popover,
    boxShadow: shadowsDark.lg,
  },
  Switch: {
    ...lightThemeOverrides.Switch,
    railColor: 'rgba(120, 120, 128, 0.32)',
  },
  Button: lightThemeOverrides.Button,
  Tag: lightThemeOverrides.Tag,
  Input: lightThemeOverrides.Input,
  Select: lightThemeOverrides.Select,
  Tabs: lightThemeOverrides.Tabs,
  Message: lightThemeOverrides.Message,
  Dialog: lightThemeOverrides.Dialog,
  Drawer: lightThemeOverrides.Drawer,
  Tooltip: lightThemeOverrides.Tooltip,
  Progress: lightThemeOverrides.Progress,
  Slider: lightThemeOverrides.Slider,
  Avatar: lightThemeOverrides.Avatar,
  Badge: lightThemeOverrides.Badge,
  Collapse: {
    ...lightThemeOverrides.Collapse,
    dividerColor: 'rgba(84, 84, 88, 0.65)',
  },
  List: lightThemeOverrides.List,
  Form: lightThemeOverrides.Form,
  Skeleton: lightThemeOverrides.Skeleton,
}

export function useTheme() {
  const themeStore = useThemeStore()

  const theme = computed<GlobalTheme | null>(() => {
    return themeStore.isDark ? darkTheme : null
  })

  const themeOverrides = computed<GlobalThemeOverrides>(() => {
    return themeStore.isDark ? darkThemeOverrides : lightThemeOverrides
  })

  const isDark = computed(() => themeStore.isDark)

  const toggleTheme = () => {
    themeStore.toggleTheme()
  }

  // 同步 dark class 到 document，用于 CSS 变量切换
  watchEffect(() => {
    if (themeStore.isDark) {
      document.documentElement.classList.add('dark')
      document.body.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
      document.body.classList.remove('dark')
    }
  })

  return {
    theme,
    themeOverrides,
    isDark,
    toggleTheme,
  }
}
