<template>
  <div class="tool-call-card" :class="{ 'is-error': isError }">
    <div class="tool-call-header">
      <v-icon size="small" :color="isError ? 'error' : 'warning'">
        {{ isError ? 'mdi-alert-circle-outline' : 'mdi-wrench' }}
      </v-icon>
      <span class="tool-name">{{ toolName }}</span>
      <v-icon v-if="isLoading" size="small" class="spin-icon" color="primary">
        mdi-loading
      </v-icon>
      <v-icon v-else-if="isError" size="small" color="error">
        mdi-close-circle
      </v-icon>
      <v-icon v-else size="small" color="success">
        mdi-check-circle
      </v-icon>
    </div>
    <div v-if="result" class="tool-call-result">
      <pre>{{ result }}</pre>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  toolName: string
  args?: any
  result?: string
  isLoading?: boolean
  isError?: boolean
}>()
</script>

<style scoped>
.tool-call-card {
  background: rgba(var(--v-theme-surface-variant), 0.3);
  border: 1px solid rgba(var(--v-border-color), 0.2);
  border-radius: 8px;
  padding: 8px 12px;
  margin: 8px 0;
  font-size: 13px;
}
.tool-call-card.is-error {
  border-color: rgba(var(--v-theme-error), 0.3);
}
.tool-call-header {
  display: flex;
  align-items: center;
  gap: 6px;
}
.tool-name {
  flex: 1;
  font-weight: 500;
}
.spin-icon {
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
.tool-call-result {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px solid rgba(var(--v-border-color), 0.1);
}
.tool-call-result pre {
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 12px;
}
</style>
