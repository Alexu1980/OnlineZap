/// <reference types="vite/client" />

declare module '@twa-dev/sdk' {
  const WebApp: {
    ready(): void
    expand(): void
    close(): void
    BackButton: {
      show(): void
      hide(): void
      onClick(callback: () => void): void
      offClick(callback: () => void): void
    }
    MainButton: {
      setText(text: string): void
      show(): void
      hide(): void
      onClick(callback: () => void): void
      offClick(callback: () => void): void
    }
    HapticFeedback: {
      notificationOccurred(type: 'success' | 'error' | 'warning'): void
    }
    HeaderColor: string
    BackgroundColor: string
    setHeaderColor(color: string): void
    setBackgroundColor(color: string): void
    isExpanded: boolean
    platform: string
    version: string
    colorScheme: 'light' | 'dark'
    themeParams: Record<string, string>
    initData: string
    initDataUnsafe: Record<string, any>
    onEvent(event: string, callback: (...args: any[]) => void): void
    offEvent(event: string, callback: (...args: any[]) => void): void
    sendData(data: string): void
    switchInitData(data: string): void
    ready: () => void
    expand: () => void
    close: () => void
  }
  export default WebApp
}
