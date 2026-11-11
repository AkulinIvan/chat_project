<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useChatStore } from './stores/chat'

const store = useChatStore()
const username = ref('')
const password = ref('')
const roomId = ref(1)
const text = ref('')
const listRef = ref(null)

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) listRef.value.scrollTop = listRef.value.scrollHeight
  })
}

async function doLogin() {
  await store.login(username.value, password.value)
  await store.fetchHistory(roomId.value)
  store.connect(roomId.value)
  scrollToBottom()
}

function sendMessage() {
  const content = text.value.trim()
  if (!content) return
  store.send(content)
  text.value = ''
}

let typingTimeout
function onInput() {
  clearTimeout(typingTimeout)
  typingTimeout = setTimeout(() => store.sendTyping(), 300)
}

watch(() => store.messages.length, scrollToBottom)

onMounted(() => {
  if (store.isAuthenticated) {
    store.fetchHistory(roomId.value).then(() => {
      store.connect(roomId.value)
      scrollToBottom()
    })
  }
})
</script>

<template>
  <div class="app">
    <h1>💬 Chat</h1>

    <!-- Login -->
    <div v-if="!store.isAuthenticated" class="login">
      <input v-model="username" placeholder="Логин" />
      <input v-model="password" type="password" placeholder="Пароль" @keyup.enter="doLogin" />
      <button @click="doLogin">Войти</button>
    </div>

    <!-- Chat -->
    <div v-else class="chat">
      <div class="toolbar">
        <span class="status" :class="{ online: store.connected }">
          {{ store.connected ? '🟢 Онлайн' : '🟡 Переподключение...' }}
        </span>
        <span v-if="store.lastError" class="error">Ошибка: {{ store.lastError }}</span>
        <button @click="store.logout()">Выйти</button>
      </div>

      <div ref="listRef" class="messages">
        <div v-for="m in store.messages" :key="m.id" class="msg" :class="{ pending: m.pending }">
          <b>{{ m.author }}</b>
          <span>{{ m.content }}</span>
          <small>{{ new Date(m.created_at).toLocaleTimeString() }}</small>
        </div>
      </div>

      <div v-if="store.typingUsers.size" class="typing">
        Кто-то печатает...
      </div>

      <div class="input">
        <input
          v-model="text"
          @input="onInput"
          @keyup.enter="sendMessage"
          placeholder="Сообщение..."
        />
        <button :disabled="!store.connected" @click="sendMessage">Отправить</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.app { max-width: 720px; margin: 0 auto; padding: 16px; font-family: system-ui, sans-serif; }
.login { display: flex; flex-direction: column; gap: 8px; max-width: 300px; }
.login input, .chat input { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
.login button, .chat button { padding: 8px 16px; cursor: pointer; }
.chat { display: flex; flex-direction: column; height: 600px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; }
.toolbar { display: flex; align-items: center; gap: 12px; padding: 8px 12px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
.status { font-size: 13px; color: #999; }
.status.online { color: #2e7d32; }
.error { color: #c62828; font-size: 12px; }
.messages { flex: 1; overflow-y: auto; padding: 12px; }
.msg { margin-bottom: 8px; line-height: 1.4; }
.msg.pending { opacity: 0.6; }
.msg b { margin-right: 6px; color: #1565c0; }
.msg small { color: #999; margin-left: 8px; font-size: 11px; }
.typing { padding: 4px 12px; font-size: 12px; color: #888; font-style: italic; }
.input { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #ddd; }
.input input { flex: 1; }
</style>