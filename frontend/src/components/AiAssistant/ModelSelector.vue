<template>
  <div class="model-selector">
    <v-select
      v-model="selectedProvider"
      :items="providers"
      item-title="title"
      item-value="value"
      :label="$t('ai.provider')"
      variant="outlined"
      density="compact"
      hide-details
      @update:model-value="onProviderChange"
    ></v-select>
    <v-text-field
      v-model="apiBaseUrl"
      :label="$t('ai.apiUrl')"
      variant="outlined"
      density="compact"
      hide-details
      class="mt-2"
    ></v-text-field>
    <v-text-field
      v-model="apiKey"
      :label="$t('ai.apiKey')"
      :type="showKey ? 'text' : 'password'"
      variant="outlined"
      density="compact"
      hide-details
      class="mt-2"
      :append-inner-icon="showKey ? 'mdi-eye-off' : 'mdi-eye'"
      @click:append-inner="showKey = !showKey"
    ></v-text-field>
    <v-row class="mt-2" dense>
      <v-col cols="6">
        <v-btn
          block
          variant="tonal"
          color="primary"
          :loading="loadingModels"
          :disabled="!apiKey || !apiBaseUrl"
          @click="$emit('fetch-models', { apiBaseUrl, apiKey })"
        >
          {{ $t('ai.getModels') }}
        </v-btn>
      </v-col>
      <v-col cols="6">
        <v-btn
          block
          variant="tonal"
          color="success"
          :loading="testing"
          :disabled="!selectedModel || !apiKey"
          @click="$emit('test-connection', { apiBaseUrl, apiKey, modelName: selectedModel })"
        >
          {{ $t('ai.testConnection') }}
        </v-btn>
      </v-col>
    </v-row>
    <v-select
      v-model="selectedModel"
      :items="modelList"
      :label="$t('ai.model')"
      variant="outlined"
      density="compact"
      hide-details
      class="mt-2"
    ></v-select>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const props = defineProps<{
  providers?: Array<{ title: string; value: string; baseUrl: string }>
  modelList?: string[]
  selectedModel?: string
  loadingModels?: boolean
  testing?: boolean
  initialApiUrl?: string
  initialApiKey?: string
  initialProvider?: string
}>()

const emit = defineEmits<{
  'fetch-models': [config: { apiBaseUrl: string; apiKey: string }]
  'test-connection': [config: { apiBaseUrl: string; apiKey: string; modelName: string }]
  'update:api-url': [url: string]
  'update:api-key': [key: string]
  'update:provider': [provider: string]
  'update:model': [model: string]
}>()

const showKey = ref(false)
const selectedProvider = ref(props.initialProvider || 'siliconflow')
const apiBaseUrl = ref(props.initialApiUrl || 'https://api.siliconflow.cn/v1')
const apiKey = ref(props.initialApiKey || '')
const selectedModel = ref(props.selectedModel || '')

const defaultProviders = [
  { title: '硅基流动 (SiliconFlow)', value: 'siliconflow', baseUrl: 'https://api.siliconflow.cn/v1' },
  { title: 'DeepSeek', value: 'deepseek', baseUrl: 'https://api.deepseek.com' },
  { title: '自定义（OpenAI 兼容）', value: 'custom', baseUrl: '' },
]

function onProviderChange(val: string) {
  const provider = defaultProviders.find(p => p.value === val)
  if (provider && provider.baseUrl) {
    apiBaseUrl.value = provider.baseUrl
    emit('update:api-url', apiBaseUrl.value)
  }
  emit('update:provider', val)
}
</script>
