<template>
  <div class="chat-message-wrapper" :class="{ 'is-user': role === 'user', 'is-assistant': role === 'assistant' }">
    <div class="chat-message" :class="role">
      <!-- 用户消息 -->
      <template v-if="role === 'user'">
        <div class="message-content user-content">
          <span>{{ content }}</span>
        </div>
      </template>

      <!-- AI 消息 -->
      <template v-else-if="role === 'assistant'">
        <div class="assistant-avatar">
          <v-icon color="primary">mdi-robot</v-icon>
        </div>
        <div class="message-content assistant-content">
          <div v-if="isStreaming" class="streaming-content" v-html="renderedContent"></div>
          <div v-else class="final-content" v-html="renderedContent"></div>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import MarkdownIt from 'markdown-it'

const md = new MarkdownIt({
  html: false,
  breaks: true,
  linkify: true,
})

const props = defineProps<{
  role: 'user' | 'assistant' | 'tool'
  content: string
  isStreaming?: boolean
}>()

const renderedContent = computed(() => {
  try {
    return md.render(props.content || '')
  } catch {
    return props.content || ''
  }
})
</script>

<style scoped>
.chat-message-wrapper {
  display: flex;
  margin-bottom: 16px;
  padding: 0 16px;
}
.chat-message-wrapper.is-user {
  justify-content: flex-end;
}
.chat-message-wrapper.is-assistant {
  justify-content: flex-start;
}
.chat-message {
  max-width: 75%;
  display: flex;
  gap: 8px;
}
.chat-message.user {
  flex-direction: row-reverse;
}
.assistant-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: rgba(var(--v-theme-primary), 0.1);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.message-content {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.5;
  font-size: 14px;
  word-break: break-word;
}
.user-content {
  background: rgb(var(--v-theme-primary));
  color: rgb(var(--v-theme-on-primary));
  border-bottom-right-radius: 4px;
}
.assistant-content {
  background: rgba(var(--v-theme-surface-variant), 0.5);
  color: rgb(var(--v-theme-on-surface));
  border-bottom-left-radius: 4px;
}
.streaming-content::after {
  content: '▍';
  animation: blink 1s step-end infinite;
}
@keyframes blink {
  50% { opacity: 0; }
}
:deep(pre) {
  background: rgba(0,0,0,0.08);
  padding: 8px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: 13px;
}
:deep(code) {
  background: rgba(0,0,0,0.06);
  padding: 2px 4px;
  border-radius: 3px;
  font-size: 13px;
}
:deep(p) {
  margin: 4px 0;
}
:deep(ul), :deep(ol) {
  padding-left: 20px;
  margin: 4px 0;
}
</style>
