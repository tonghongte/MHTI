<script setup lang="ts">
import { computed } from 'vue'
import type { Component } from 'vue'

/**
 * StatusBadge 组件
 * iOS 风格的状态徽章，支持多种状态类型和动画效果
 */

export type BadgeStatus = 'success' | 'warning' | 'error' | 'info' | 'pending' | 'default'
export type BadgeSize = 'small' | 'medium' | 'large'

const props = withDefaults(defineProps<{
  /** 状态类型 */
  status?: BadgeStatus
  /** 徽章文本 */
  text?: string
  /** 尺寸 */
  size?: BadgeSize
  /** 是否显示脉冲动画（用于进行中状态） */
  pulse?: boolean
  /** 是否仅显示圆点（不显示文本） */
  dot?: boolean
  /** 自定义图标 */
  icon?: Component
  /** 是否圆角（胶囊形状） */
  round?: boolean
}>(), {
  status: 'default',
  size: 'medium',
  pulse: false,
  dot: false,
  round: true,
})

// 状态对应的颜色映射
const statusColors: Record<BadgeStatus, { bg: string; text: string; dot: string }> = {
  success: {
    bg: 'rgba(52, 199, 89, 0.15)',
    text: '#34C759',
    dot: '#34C759',
  },
  warning: {
    bg: 'rgba(255, 149, 0, 0.15)',
    text: '#FF9500',
    dot: '#FF9500',
  },
  error: {
    bg: 'rgba(255, 59, 48, 0.15)',
    text: '#FF3B30',
    dot: '#FF3B30',
  },
  info: {
    bg: 'rgba(90, 200, 250, 0.15)',
    text: '#5AC8FA',
    dot: '#5AC8FA',
  },
  pending: {
    bg: 'rgba(255, 204, 0, 0.15)',
    text: '#FFCC00',
    dot: '#FFCC00',
  },
  default: {
    bg: 'rgba(142, 142, 147, 0.15)',
    text: '#8E8E93',
    dot: '#8E8E93',
  },
}

// 尺寸映射
const sizeConfig: Record<BadgeSize, { height: string; fontSize: string; padding: string; dotSize: string }> = {
  small: {
    height: '20px',
    fontSize: '11px',
    padding: '0 6px',
    dotSize: '6px',
  },
  medium: {
    height: '24px',
    fontSize: '12px',
    padding: '0 8px',
    dotSize: '8px',
  },
  large: {
    height: '28px',
    fontSize: '13px',
    padding: '0 10px',
    dotSize: '10px',
  },
}

// 计算样式
const badgeStyle = computed(() => {
  const colors = statusColors[props.status]
  const sizes = sizeConfig[props.size]

  if (props.dot) {
    return {
      width: sizes.dotSize,
      height: sizes.dotSize,
      backgroundColor: colors.dot,
      borderRadius: '50%',
    }
  }

  return {
    height: sizes.height,
    fontSize: sizes.fontSize,
    padding: sizes.padding,
    backgroundColor: colors.bg,
    color: colors.text,
    borderRadius: props.round ? sizes.height : '6px',
  }
})

// 圆点样式
const dotStyle = computed(() => {
  const colors = statusColors[props.status]
  return {
    backgroundColor: colors.dot,
  }
})

// 类名
const badgeClass = computed(() => ({
  'status-badge': true,
  'status-badge--dot-only': props.dot,
  'status-badge--pulse': props.pulse,
  [`status-badge--${props.status}`]: true,
  [`status-badge--${props.size}`]: true,
}))
</script>

<template>
  <span :class="badgeClass" :style="badgeStyle">
    <!-- 仅圆点模式 -->
    <template v-if="dot">
      <span class="status-badge__dot-inner" :style="dotStyle" />
    </template>

    <!-- 完整徽章模式 -->
    <template v-else>
      <!-- 状态指示点 -->
      <span v-if="!icon" class="status-badge__dot" :style="dotStyle" />

      <!-- 自定义图标 -->
      <component :is="icon" v-if="icon" class="status-badge__icon" />

      <!-- 文本 -->
      <span v-if="text" class="status-badge__text">{{ text }}</span>

      <!-- 默认插槽 -->
      <slot v-else />
    </template>
  </span>
</template>

<style scoped>
.status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-weight: 500;
  white-space: nowrap;
  vertical-align: middle;
  line-height: 1;
}

/* 状态指示点 */
.status-badge__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 仅圆点模式 */
.status-badge--dot-only {
  padding: 0;
}

.status-badge__dot-inner {
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

/* 图标 */
.status-badge__icon {
  width: 12px;
  height: 12px;
  flex-shrink: 0;
}

/* 文本 */
.status-badge__text {
  line-height: 1;
}

/* 脉冲动画 */
.status-badge--pulse .status-badge__dot,
.status-badge--pulse.status-badge--dot-only .status-badge__dot-inner {
  animation: badge-pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
}

@keyframes badge-pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* 成功状态脉冲 - 使用呼吸光晕效果 */
.status-badge--success.status-badge--pulse .status-badge__dot,
.status-badge--success.status-badge--pulse.status-badge--dot-only .status-badge__dot-inner {
  animation: badge-pulse-success 2s ease-in-out infinite;
}

@keyframes badge-pulse-success {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(52, 199, 89, 0.4);
  }
  50% {
    box-shadow: 0 0 0 4px rgba(52, 199, 89, 0);
  }
}

/* 进行中状态 - 旋转动画 */
.status-badge--pending.status-badge--pulse .status-badge__dot,
.status-badge--pending.status-badge--pulse.status-badge--dot-only .status-badge__dot-inner {
  animation: badge-spin 1s linear infinite;
}

@keyframes badge-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 错误状态 - 闪烁效果 */
.status-badge--error.status-badge--pulse .status-badge__dot,
.status-badge--error.status-badge--pulse.status-badge--dot-only .status-badge__dot-inner {
  animation: badge-blink 1s ease-in-out infinite;
}

@keyframes badge-blink {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
  .status-badge--pulse .status-badge__dot,
  .status-badge--pulse.status-badge--dot-only .status-badge__dot-inner {
    animation: none;
  }
}
</style>
