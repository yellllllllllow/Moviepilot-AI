<template>
  <div class="session-list">
    <div class="session-list-header">
      <v-btn
        block
        color="primary"
        variant="tonal"
        prepend-icon="mdi-plus"
        @click="$emit('new-session')"
      >
        {{ $t('common.create') }}
      </v-btn>
    </div>
    <v-list
      class="session-items"
      nav
      density="compact"
    >
      <v-list-item
        v-for="session in sessions"
        :key="session.id"
        :active="session.id === activeId"
        :title="session.title || '新对话'"
        :subtitle="formatTime(session.updated_at)"
        density="compact"
        class="session-item"
        @click="$emit('select-session', session.id)"
      >
        <template v-slot:prepend>
          <v-icon size="small">mdi-chat-outline</v-icon>
        </template>
        <template v-slot:append>
          <v-btn
            icon="mdi-close"
            size="x-small"
            variant="text"
            density="compact"
            @click.stop="$emit('delete-session', session.id)"
          ></v-btn>
        </template>
      </v-list-item>
    </v-list>
    <div v-if="sessions.length === 0" class="no-sessions">
      <v-icon size="48" color="disabled">mdi-chat-outline</v-icon>
      <p class="text-disabled mt-2">{{ $t('common.noData') }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ChatSession } from '@/stores/types'

defineProps<{
  sessions: ChatSession[]
  activeId: number | null
}>()

defineEmits<{
  'new-session': []
  'select-session': [id: number]
  'delete-session': [id: number]
}>()

function formatTime(dateStr: string): string {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2, '0')}`
}
</script>

<style scoped>
.session-list {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.session-list-header {
  padding: 12px;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.1);
}
.session-items {
  flex: 1;
  overflow-y: auto;
}
.session-item {
  cursor: pointer;
}
.no-sessions {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
</style>
