import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ChatMessage, ChatSession } from './types'

export const useAiStore = defineStore('ai', () => {
  // 对话列表
  const sessions = ref<ChatSession[]>([])
  // 当前对话
  const currentSessionId = ref<number | null>(null)
  // 当前消息列表
  const messages = ref<ChatMessage[]>([])
  // 是否正在加载
  const loading = ref(false)
  // AI 是否正在回复
  const aiResponding = ref(false)
  // 当前对话标题
  const currentTitle = ref('')

  function setSessions(list: ChatSession[]) {
    sessions.value = list
  }

  function setCurrentSession(id: number | null) {
    currentSessionId.value = id
  }

  function setMessages(list: ChatMessage[]) {
    messages.value = list
  }

  function addMessage(msg: ChatMessage) {
    messages.value.push(msg)
  }

  function updateLastMessage(content: string) {
    if (messages.value.length > 0) {
      const last = messages.value[messages.value.length - 1]
      if (last.role === 'assistant') {
        last.content = content
      }
    }
  }

  function setLoading(val: boolean) {
    loading.value = val
  }

  function setAiResponding(val: boolean) {
    aiResponding.value = val
  }

  function setCurrentTitle(title: string) {
    currentTitle.value = title
  }

  function removeSession(id: number) {
    sessions.value = sessions.value.filter(s => s.id !== id)
    if (currentSessionId.value === id) {
      currentSessionId.value = null
      messages.value = []
    }
  }

  return {
    sessions,
    currentSessionId,
    messages,
    loading,
    aiResponding,
    currentTitle,
    setSessions,
    setCurrentSession,
    setMessages,
    addMessage,
    updateLastMessage,
    setLoading,
    setAiResponding,
    setCurrentTitle,
    removeSession,
  }
})
