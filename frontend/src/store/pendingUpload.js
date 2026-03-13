/**
 * 临时存储待上传的文件和需求
 * 用于首页点击启动引擎后立即跳转，在Process页面再进行API调用
 */
import { reactive } from 'vue'

const state = reactive({
  files: [],
  simulationRequirement: '',
  focusEntities: '',
  focusEvents: '',
  isPending: false
})

export function setPendingUpload(files, requirement, focusEntities = '', focusEvents = '') {
  state.files = files
  state.simulationRequirement = requirement
  state.focusEntities = focusEntities
  state.focusEvents = focusEvents
  state.isPending = true
}

export function getPendingUpload() {
  return {
    files: state.files,
    simulationRequirement: state.simulationRequirement,
    focusEntities: state.focusEntities,
    focusEvents: state.focusEvents,
    isPending: state.isPending
  }
}

export function clearPendingUpload() {
  state.files = []
  state.simulationRequirement = ''
  state.focusEntities = ''
  state.focusEvents = ''
  state.isPending = false
}

export default state
