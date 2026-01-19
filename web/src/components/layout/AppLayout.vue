<script setup lang="ts">
import { ref, computed, watch, provide } from 'vue'
import { useRoute } from 'vue-router'
import { NLayout, NLayoutHeader, NLayoutSider, NLayoutContent } from 'naive-ui'
import { useTheme } from '@/composables/useTheme'
import { useMobileLayout } from '@/composables/useMobileLayout'
import AppHeader from './AppHeader.vue'
import AppSidebar from './AppSidebar.vue'
import MobileTabBar from './MobileTabBar.vue'
import MobileDrawer from './MobileDrawer.vue'

/**
 * AppLayout - 响应式应用布局
 *
 * 布局模式：
 * - 桌面端 (>=1024px): 侧边栏展开 + 顶部导航
 * - 平板端 (768-1023px): 侧边栏折叠 + 顶部导航
 * - 移动端 (<768px): 底部 TabBar + 抽屉菜单
 */

const route = useRoute()
const { isDark } = useTheme()
const { isMobile, isTablet, sidebarMode } = useMobileLayout()

// 侧边栏状态
const sidebarCollapsed = ref(false)
const mobileDrawerShow = ref(false)

// 根据屏幕尺寸自动调整侧边栏状态
watch(sidebarMode, (mode) => {
  if (mode === 'hidden') {
    sidebarCollapsed.value = true
  } else if (mode === 'collapsed') {
    sidebarCollapsed.value = true
  } else {
    sidebarCollapsed.value = false
  }
}, { immediate: true })

// 是否显示侧边栏
const showSidebar = computed(() => !isMobile.value)

// 是否显示底部 TabBar
const showTabBar = computed(() => isMobile.value)

// 是否是无布局页面（如登录页）
const isFullPage = computed(() => {
  return route.meta.fullPage === true || route.name === 'login'
})

// 内容区域样式
const contentStyle = computed(() => {
  const padding = isMobile.value ? '16px' : '24px'
  const paddingBottom = isMobile.value ? 'calc(16px + var(--tabbar-height, 56px) + env(safe-area-inset-bottom, 0))' : '24px'
  return {
    padding,
    paddingBottom,
  }
})

// 打开移动端抽屉
function openMobileDrawer() {
  mobileDrawerShow.value = true
}

// 关闭移动端抽屉
function closeMobileDrawer() {
  mobileDrawerShow.value = false
}

// 手动切换侧边栏
function toggleSidebar() {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 提供布局状态给子组件
provide('layout', {
  sidebarCollapsed,
  mobileDrawerShow,
  openMobileDrawer,
  closeMobileDrawer,
  toggleSidebar,
})
</script>

<template>
  <!-- 全页面模式（登录页等） -->
  <template v-if="isFullPage">
    <router-view />
  </template>

  <!-- 正常布局模式 -->
  <template v-else>
    <NLayout class="app-layout" :has-sider="showSidebar" position="absolute">
      <!-- 桌面端/平板端侧边栏 -->
      <NLayoutSider
        v-if="showSidebar"
        bordered
        collapse-mode="width"
        :collapsed-width="72"
        :width="240"
        :collapsed="sidebarCollapsed"
        :show-trigger="!isTablet"
        :native-scrollbar="false"
        class="app-sider"
        :class="{ dark: isDark }"
        @collapse="sidebarCollapsed = true"
        @expand="sidebarCollapsed = false"
      >
        <!-- Logo 区域 -->
        <div class="sider-header" :class="{ collapsed: sidebarCollapsed }">
          <div class="logo-wrapper">
            <div class="logo-icon">
              <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <rect x="3" y="3" width="18" height="18" rx="4" stroke="currentColor" stroke-width="2"/>
                <path d="M8 12L11 15L16 9" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </div>
            <transition name="logo-fade">
              <span v-if="!sidebarCollapsed" class="logo-text">MHTI</span>
            </transition>
          </div>
        </div>
        <AppSidebar :collapsed="sidebarCollapsed" />
      </NLayoutSider>

      <NLayout>
        <!-- 顶部导航栏 -->
        <NLayoutHeader bordered class="app-header-wrapper" :class="{ dark: isDark, mobile: isMobile }" position="absolute">
          <AppHeader
            :show-menu-button="isMobile"
            @menu-click="openMobileDrawer"
          />
        </NLayoutHeader>

        <!-- 主内容区域 -->
        <NLayoutContent
          :content-style="contentStyle"
          class="app-content"
          :class="{ dark: isDark, 'has-tabbar': showTabBar }"
          :native-scrollbar="false"
        >
          <router-view v-slot="{ Component }">
            <transition name="ios-page" mode="out-in">
              <component :is="Component" />
            </transition>
          </router-view>
        </NLayoutContent>
      </NLayout>
    </NLayout>

    <!-- 移动端底部 TabBar -->
    <MobileTabBar v-if="showTabBar" />

    <!-- 移动端侧边抽屉 -->
    <MobileDrawer
      v-model:show="mobileDrawerShow"
      placement="left"
    >
      <template #title>菜单</template>
      <!-- 抽屉内的导航菜单 -->
      <AppSidebar :collapsed="false" @navigate="closeMobileDrawer" />
    </MobileDrawer>
  </template>
</template>

<style scoped>
.app-layout {
  min-height: 100vh;
}

/* iOS 风格侧边栏 - 毛玻璃效果 */
.app-sider {
  background: var(--glass-bg-thick, rgba(255, 255, 255, 0.85)) !important;
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-right: 1px solid var(--glass-border, rgba(255, 255, 255, 0.2)) !important;
  box-shadow: 1px 0 0 var(--glass-border, rgba(255, 255, 255, 0.2));
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.app-sider.dark {
  background: var(--glass-bg-thick, rgba(30, 30, 30, 0.85)) !important;
}

/* 侧边栏触发器样式 */
.app-sider :deep(.n-layout-toggle-button) {
  background: var(--color-bg-secondary, #f5f5f5);
  border: 1px solid var(--glass-border, rgba(0, 0, 0, 0.1));
  border-radius: 50%;
  box-shadow: var(--shadow-sm, 0 1px 2px rgba(0, 0, 0, 0.05));
  transition: all 0.2s ease;
}

.app-sider :deep(.n-layout-toggle-button:hover) {
  background: rgba(0, 122, 255, 0.1);
  box-shadow: var(--shadow-md, 0 2px 8px rgba(0, 0, 0, 0.1));
}

/* Logo 区域 */
.sider-header {
  height: var(--header-height, 64px);
  display: flex;
  align-items: center;
  justify-content: center;
  border-bottom: 1px solid var(--border-color, rgba(0, 0, 0, 0.08));
  padding: 0 20px;
  transition: all 0.3s ease;
}

.sider-header.collapsed {
  padding: 0 12px;
}

.logo-wrapper {
  display: flex;
  align-items: center;
  gap: 12px;
}

.logo-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-primary, #007aff);
  border-radius: 12px;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0, 122, 255, 0.3);
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), box-shadow 0.3s ease;
}

.logo-icon:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(0, 122, 255, 0.4);
}

.logo-icon svg {
  width: 22px;
  height: 22px;
}

.logo-text {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-primary, #007aff);
  white-space: nowrap;
  letter-spacing: -0.5px;
}

/* iOS 风格头部 - 毛玻璃效果 */
.app-header-wrapper {
  height: var(--header-height, 64px);
  background: var(--glass-bg-thick, rgba(255, 255, 255, 0.85)) !important;
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  border-bottom: 1px solid var(--glass-border, rgba(0, 0, 0, 0.08)) !important;
  box-shadow: 0 1px 0 var(--glass-border, rgba(0, 0, 0, 0.08));
}

.app-header-wrapper.dark {
  background: var(--glass-bg-thick, rgba(30, 30, 30, 0.85)) !important;
}

.app-header-wrapper.mobile {
  /* 移动端安全区域适配 */
  padding-top: env(safe-area-inset-top, 0);
}

/* 内容区域 */
.app-content {
  min-height: calc(100vh - var(--header-height, 64px));
  background: var(--color-bg-primary, #f2f2f7);
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.app-content.dark {
  background: var(--color-bg-primary, #000);
}

.app-content.has-tabbar {
  /* 为底部 TabBar 预留空间 */
  min-height: calc(100vh - var(--header-height, 64px) - var(--tabbar-height, 56px) - env(safe-area-inset-bottom, 0));
}

/* iOS 风格页面切换动画 */
.ios-page-enter-active {
  animation: ios-slide-in 0.35s ease;
}

.ios-page-leave-active {
  animation: ios-slide-out 0.2s ease;
}

@keyframes ios-slide-in {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes ios-slide-out {
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-8px);
  }
}

/* Logo 文字淡入淡出 */
.logo-fade-enter-active,
.logo-fade-leave-active {
  transition: opacity 0.25s ease, transform 0.25s ease;
}

.logo-fade-enter-from {
  opacity: 0;
  transform: translateX(-8px);
}

.logo-fade-leave-to {
  opacity: 0;
  transform: translateX(-8px);
}

/* 减少动画 */
@media (prefers-reduced-motion: reduce) {
  .ios-page-enter-active,
  .ios-page-leave-active {
    animation: none;
  }

  .logo-fade-enter-active,
  .logo-fade-leave-active {
    transition: none;
  }
}
</style>
