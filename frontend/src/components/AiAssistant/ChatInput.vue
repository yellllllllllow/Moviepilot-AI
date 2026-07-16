<template>
  <div class="chat-input-wrapper">
    <v-textarea
      v-model="inputText"
      class="chat-input"
      :placeholder="$t('common.inputMessage')"
      auto-grow
      rows="1"
      max-rows="4"
      variant="outlined"
      hide-details
      :disabled="disabled"
      @keydown.enter.exact.prevent="handleSend"
      @keydown.shift.enter="handleShiftEnter"
    ></v-textarea>
    <v-btn
      icon
      color="primary"
      class="send-btn"
      :disabled="!inputText.trim() || disabled"
      :loading="loading"
      @click="handleSend"
    >
      <v-icon>mdi-send</v-icon>
    </v-btn>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  loading?: boolean
  disabled?: boolean
}>()

const emit = defineEmits<{
  send: [message: string]
}>()

const inputText = ref('')

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.disabled) return
  emit('send', text)
  inputText.value = ''
}

function handleShiftEnter(e: KeyboardEvent) {
  const target = e.target as HTMLTextAreaElement
  const start = target.selectionStart
  const end = target.selectionEnd
  inputText.value = inputText.value.substring(0, start) + '\n' + inputText.value.substring(end)
}
</script>

<style scoped>
.chat-input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(var(--v-border-color), 0.1);
}
.chat-input {
  flex: 1;
}
.send-btn {
  margin-bottom: 4px;
}
</style>
