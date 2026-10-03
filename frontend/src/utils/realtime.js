/**
 * 实时聊天连接（独立零件）。
 *
 * 把 socket.io 的连接、事件分发、在线状态封装起来，
 * 页面只关心「收到消息 / 被断开」这类业务事件。
 *
 * 后端同时提供原生 WebSocket（``/api/v1/chat/ws``），
 * 这里用 socket.io 是因为它自带断线重连与房间能力。
 */
import { io } from 'socket.io-client'

//: socket.io 挂载路径（后端 mount 在 /ws 下）
export const SOCKET_PATH = '/ws/socket.io'

/**
 * 建立聊天连接。
 *
 * @param {object} options
 * @param {string} options.token  访问令牌（握手时通过 auth 载荷传递）
 * @param {object} options.handlers 事件回调：
 *        ``onMessage`` / ``onRevoked`` / ``onNotification`` /
 *        ``onUserJoined`` / ``onStatusChange``
 * @returns {{socket: object, send: Function, recall: Function, close: Function}}
 */
export function createChatSocket({ token, handlers = {} }) {
  const {
    onMessage,
    onRevoked,
    onNotification,
    onUserJoined,
    onStatusChange,
    onError,
  } = handlers

  const socket = io('/', {
    path: SOCKET_PATH,
    transports: ['websocket'],
    // 令牌通过 socket.io 的 auth 载荷传递（握手时无法自定义请求头）
    auth: { token },
  })

  socket.on('connect', () => onStatusChange?.(true))
  socket.on('disconnect', () => onStatusChange?.(false))
  socket.on('connect_error', (error) => {
    onStatusChange?.(false)
    onError?.(`聊天连接失败：${error.message}`)
  })

  socket.on('chat_message', (payload) => {
    if (payload) onMessage?.(payload)
  })
  socket.on('message_revoked', (payload) => onRevoked?.(payload))
  socket.on('notification', (payload) => onNotification?.(payload))
  socket.on('user_joined', (payload) => onUserJoined?.(payload))

  return {
    socket,

    /** 发送消息；后端会用 ack 回执 ``{ok, id, detail}``。 */
    send(content) {
      socket.emit('send_message', { content }, (reply) => {
        if (reply && reply.ok === false) {
          onError?.(reply.detail || '发送失败')
        }
      })
    },

    /** 撤回消息。 */
    recall(id) {
      socket.emit('revoke_message', { id }, (reply) => {
        if (reply && reply.ok === false) {
          onError?.(reply.detail || '撤回失败')
        }
      })
    },

    get connected() {
      return Boolean(socket.connected)
    },

    close() {
      socket.disconnect()
    },
  }
}

export default createChatSocket
