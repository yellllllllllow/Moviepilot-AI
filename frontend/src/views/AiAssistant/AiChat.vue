<template>
  <div class="ai-chat-page">
    <!-- 左侧：对话列表 -->
    <div class="chat-sidebar">
      <ChatSessionList
        :sessions="aiStore.sessions"
        :active-id="aiStore.currentSessionId"
        @new-session="handleNewSession"
        @select-session="handleSelectSession"
        @delete-session="handleDeleteSession"
      />
    </div>

    <!-- 右侧：聊天区域 -->
    <div class="chat-main">
      <!-- 聊天头部 -->
      <div class="chat-header">
        <span class="text-h6">{{ aiStore.currentTitle || 'AI 对话' }}</span>
        <span v-if="aiStore.aiResponding" class="ai-status">
          <v-icon size="small" color="primary" class="spin-icon">mdi-loading</v-icon>
          AI 思考中...
        </span>
      </div>

      <!-- 消息区域 -->
      <div class="chat-messages" ref="messagesRef">
        <ChatMessage
          v-for="(msg, idx) in aiStore.messages"
          :key="idx"
          :role="msg.role"
          :content="msg.content"
          :is-streaming="msg.role === 'assistant' && idx === aiStore.messages.length - 1 && aiStore.aiResponding"
        />

        <!-- 工具调用卡片 -->
        <div v-for="(tc, idx) in toolCalls" :key="'tc-' + idx" class="px-4">
          <ToolCallCard
            :tool-name="tc.toolName"
            :args="tc.args"
            :result="tc.result"
            :is-loading="tc.isLoading"
            :is-error="tc.isError"
          />
        </div>

        <!-- 空状态 -->
        <div v-if="aiStore.messages.length === 0 && !aiStore.aiResponding" class="empty-state">
          <v-icon size="64" color="disabled">mdi-robot-outline</v-icon>
          <h3 class="text-h6 mt-4 text-disabled">开始 AI 对话</h3>
          <p class="text-disabled mt-2">使用自然语言操控 MoviePilot</p>
        </div>
      </div>

      <!-- 输入区域 -->
      <ChatInput
        :loading="aiStore.aiResponding"
        :disabled="aiStore.aiResponding"
        @send="handleSendMessage"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useAiStore } from '@/stores/ai'
import { sendChatMessage, listSessions, getSessionMessages, deleteSession } from '@/api/ai'
import ChatMessage from '@/components/AiAssistant/ChatMessage.vue'
import ChatInput from '@/components/AiAssistant/ChatInput.vue'
import ChatSessionList from '@/components/AiAssistant/ChatSessionList.vue'
import ToolCallCard from '@/components/AiAssistant/ToolCallCard.vue'

const aiStore = useAiStore()
const messagesRef = ref<HTMLElement | null>(null)

interface ToolCallItem {
  toolName: string
  args?: any
  result?: string
  isLoading: boolean
  isError: boolean
}
const toolCalls = ref<ToolCallItem[]>([])

let abortController: AbortController | null = null

// 滚动到底部
async function scrollToBottom() {
  await nextTick()
  if (messagesRef.value) {
    messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }
}

// 加载对话列表
async function loadSessions() {
  try {
    const result = await listSessions()
    if (result.success) {
      aiStore.setSessions(result.data || [])
    }
  } catch {
    // ignore
  }
}

// 加载消息
async function loadMessages(sessionId: number) {
  try {
    const result = await getSessionMessages(sessionId)
    if (result.success) {
      aiStore.setMessages(result.data.messages || [])
      aiStore.setCurrentTitle(result.data.session?.title || 'AI 对话')
    }
  } catch {
    // ignore
  }
}

// 新对话
function handleNewSession() {
  abortController?.abort()
  aiStore.setCurrentSession(null)
  aiStore.setMessages([])
  aiStore.setCurrentTitle('新对话')
  toolCalls.value = []
}

// 选择对话
async function handleSelectSession(id: number) {
  abortController?.abort()
  aiStore.setCurrentSession(id)
  toolCalls.value = []
  aiStore.setAiResponding(false)
  await loadMessages(id)
  await scrollToBottom()
}

// 删除对话
async function handleDeleteSession(id: number) {
  try {
    await deleteSession(id)
    aiStore.removeSession(id)
    if (aiStore.currentSessionId === id) {
      handleNewSession()
    }
  } catch {
    // ignore
  }
}

// 发送消息
async function handleSendMessage(message: string) {
  if (!message.trim()) return

  abortController?.abort()
  abortController = new AbortController()

  // 添加用户消息
  aiStore.addMessage({
    role: 'user',
    content: message,
    tool_calls: null,
    created_at: new Date().toISOString(),
  })

  aiStore.setAiResponding(true)
  toolCalls.value = []

  // 添加一个空的 AI 消息用于流式
  const aiMsgIdx = aiStore.messages.length
  aiStore.addMessage({
    role: 'assistant',
    content: '',
    tool_calls: null,
    created_at: new Date().toISOString(),
  })

  await scrollToBottom()

  const currentSessionId = aiStore.currentSessionId

  await sendChatMessage(
    currentSessionId,
    message,
    // onDelta
    (text: string) => {
      const msgs = aiStore.messages
      if (msgs.length > 0) {
        msgs[msgs.length - 1].content += text
      }
      scrollToBottom()
    },
    // onToolStart
    (tool: string, args: any) => {
      toolCalls.value.push({
        toolName: tool,
        args,
        isLoading: true,
        isError: false,
      })
      scrollToBottom()
    },
    // onToolEnd
    (tool: string, result: string) => {
      const tc = toolCalls.value.find(t => t.toolName === tool && t.isLoading)
      if (tc) {
        tc.isLoading = false
        tc.result = result
      }
      scrollToBottom()
    },
    // onDone
    async (sessionId: number, fullResponse: string) => {
      aiStore.setAiResponding(false)
      aiStore.setCurrentSession(sessionId)

      // 更新 AI 消息
      aiStore.updateLastMessage(fullResponse)

      // 刷新对话列表
      await loadSessions()
      scrollToBottom()
    },
    // onError
    (error: string) => {
      aiStore.setAiResponding(false)
      const msgs = aiStore.messages
      if (msgs.length > 0) {
        msgs[msgs.length - 1].content = `\n\n**错误**: ${error}`
      }
      scrollToBottom()
    },
    abortController.signal,
  )
}

onMounted(async () => {
  await loadSessions()
})

onUnmounted(() => {
  abortController?.abort()
})
</script>

<style scoped>
.ai-chat-page {
  display: flex;
  height: calc(100vh - 120px);
  overflow: hidden;
}
.chat-sidebar {
  width: 280px;
  flex-shrink: 0;
  border-right: 1px solid rgba(var(--v-border-color), 0.1);
  overflow: hidden;
}
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.1);
}
.ai-status {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: rgb(var(--v-theme-primary));
}
.spin-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px 0;
}
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}
</style>
