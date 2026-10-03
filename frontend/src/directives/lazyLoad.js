const lazyLoad = {
  mounted(el, binding) {
    // 已经是最终地址就不必观察
    if (el.src === binding.value) {
      return
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            el.src = binding.value
            observer.unobserve(el)
          }
        })
      },
      { rootMargin: '100px' },
    )
    el._lazyObserver = observer
    observer.observe(el)
  },

  updated(el, binding) {
    // 地址变化时直接更新，并停止观察旧地址
    if (binding.value !== binding.oldValue) {
      el.src = binding.value
      el._lazyObserver?.unobserve(el)
    }
  },

  unmounted(el) {
    if (el._lazyObserver) {
      el._lazyObserver.unobserve(el)
      delete el._lazyObserver
    }
  },
}

export default {
  install(app) {
    app.directive('lazy-load', lazyLoad)
  },
}
