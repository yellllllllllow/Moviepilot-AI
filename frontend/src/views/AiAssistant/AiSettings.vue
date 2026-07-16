<template>
  <div class="ai-settings-page">
    <v-card class="pa-4">
      <v-card-title class="text-h5 mb-4">
        <v-icon class="mr-2">mdi-robot</v-icon>
        AI 设置
      </v-card-title>

      <v-card-text>
        <!-- 服务商选择 -->
        <v-select
          v-model="form.provider_name"
          :items="providers"
          item-title="title"
          item-value="value"
          label="模型服务商"
          variant="outlined"
          density="compact"
          class="mb-3"
          @update:model-value="onProviderChange"
        ></v-select>

        <!-- API 地址 -->
        <v-text-field
          v-model="form.api_base_url"
          label="API 地址"
          variant="outlined"
          density="compact"
          class="mb-3"
        ></v-text-field>

        <!-- API Key -->
        <v-text-field
          v-model="form.api_key"
          label="API Key"
          :type="showKey ? 'text' : 'password'"
          variant="outlined"
          density="compact"
          class="mb-3"
          :append-inner-icon="showKey ? 'mdi-eye-off' : 'mdi-eye'"
          @click:append-inner="showKey = !showKey"
        ></v-text-field>

        <!-- 获取模型列表 & 测试连接 -->
        <v-row dense class="mb-3">
          <v-col cols="6">
            <v-btn
              block
              variant="tonal"
              color="primary"
              :loading="loadingModels"
              :disabled="!form.api_key || !form.api_base_url"
              @click="handleFetchModels"
            >
              <v-icon start>mdi-cloud-download</v-icon>
              获取模型列表
            </v-btn>
          </v-col>
          <v-col cols="6">
            <v-btn
              block
              variant="tonal"
              color="success"
              :loading="testing"
              :disabled="!form.model_name || !form.api_key"
              @click="handleTestConnection"
            >
              <v-icon start>mdi-connection</v-icon>
              测试连接
            </v-btn>
          </v-col>
        </v-row>

        <!-- 模型选择 -->
        <v-select
          v-model="form.model_name"
          :items="modelList"
          label="选择模型"
          variant="outlined"
          density="compact"
          class="mb-3"
          :loading="loadingModels"
        ></v-select>

        <!-- 模型参数 -->
        <v-row dense class="mb-3">
          <v-col cols="6">
            <v-slider
              v-model="form.temperature"
              label="Temperature"
              min="0"
              max="2"
              step="0.1"
              thumb-label
              density="compact"
            ></v-slider>
            <div class="text-caption text-disabled text-center">当前值: {{ form.temperature }}</div>
          </v-col>
          <v-col cols="6">
            <v-text-field
              v-model.number="form.max_tokens"
              label="Max Tokens"
              type="number"
              variant="outlined"
              density="compact"
              :min="1"
              :max="32768"
            ></v-text-field>
          </v-col>
        </v-row>

        <!-- 系统提示词 -->
        <v-textarea
          v-model="form.system_prompt"
          label="系统提示词"
          variant="outlined"
          density="compact"
          rows="4"
          class="mb-3"
          placeholder="你是一个 MoviePilot 媒体库管理助手..."
        ></v-textarea>

        <!-- 保存按钮 -->
        <v-btn
          block
          color="primary"
          size="large"
          :loading="saving"
          :disabled="!isFormValid"
          @click="handleSave"
        >
          <v-icon start>mdi-content-save</v-icon>
          保存配置
        </v-btn>
      </v-card-text>
    </v-card>

    <!-- 提示消息 -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
    >
      {{ snackbar.message }}
    </v-snackbar>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { fetchModels, saveProvider, getProvider, testConnection } from '@/api/ai'

const providers = [
  { title: '硅基流动 (SiliconFlow)', value: 'siliconflow', baseUrl: 'https://api.siliconflow.cn/v1' },
  { title: 'DeepSeek', value: 'deepseek', baseUrl: 'https://api.deepseek.com' },
  { title: '自定义（OpenAI 兼容）', value: 'custom', baseUrl: '' },
]

const form = reactive({
  provider_name: 'siliconflow',
  api_base_url: 'https://api.siliconflow.cn/v1',
  api_key: '',
  model_name: '',
  temperature: 0.7,
  max_tokens: 4096,
  system_prompt: '你是一个 MoviePilot 媒体库管理助手。你可以帮助用户搜索媒体资源、添加订阅、管理下载任务等。请用中文友好地回复用户。',
})

const showKey = ref(false)
const loadingModels = ref(false)
const testing = ref(false)
const saving = ref(false)
const modelList = ref<string[]>([])
const snackbar = reactive({
  show: false,
  message: '',
  color: 'success',
})

const isFormValid = computed(() => {
  return form.api_base_url && form.api_key && form.model_name
})

function onProviderChange(val: string) {
  const provider = providers.find(p => p.value === val)
  if (provider && provider.baseUrl) {
    form.api_base_url = provider.baseUrl
  }
}

async function handleFetchModels() {
  loadingModels.value = true
  try {
    const result = await fetchModels(form.api_base_url, form.api_key)
    if (result.success && result.data) {
      modelList.value = result.data.map((m: any) => m.id || m.name || m)
      showSnackbar('获取模型列表成功', 'success')
    }
  } catch (e: any) {
    showSnackbar(e.message || '获取模型列表失败', 'error')
  } finally {
    loadingModels.value = false
  }
}

async function handleTestConnection() {
  testing.value = true
  try {
    const result = await testConnection(form.api_base_url, form.api_key, form.model_name)
    if (result.success) {
      showSnackbar('连接成功 ✓', 'success')
    }
  } catch (e: any) {
    showSnackbar(e.message || '连接测试失败', 'error')
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    const result = await saveProvider({
      provider_name: form.provider_name,
      api_base_url: form.api_base_url,
      api_key: form.api_key,
      model_name: form.model_name,
      temperature: form.temperature,
      max_tokens: form.max_tokens,
      system_prompt: form.system_prompt,
    })
    if (result.success) {
      showSnackbar('配置保存成功', 'success')
    }
  } catch (e: any) {
    showSnackbar(e.message || '保存配置失败', 'error')
  } finally {
    saving.value = false
  }
}

function showSnackbar(message: string, color: string) {
  snackbar.message = message
  snackbar.color = color
  snackbar.show = true
}

// 加载已有配置
onMounted(async () => {
  try {
    const result = await getProvider()
    if (result.success && result.data) {
      form.provider_name = result.data.provider_name || 'siliconflow'
      form.api_base_url = result.data.api_base_url || 'https://api.siliconflow.cn/v1'
      form.model_name = result.data.model_name || ''
      form.temperature = result.data.temperature ?? 0.7
      form.max_tokens = result.data.max_tokens ?? 4096
      form.system_prompt = result.data.system_prompt || ''
      // API Key 已脱敏，需要用户重新输入
    }
  } catch {
    // 忽略加载错误
  }
})
</script>

<style scoped>
.ai-settings-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
}
</style>
