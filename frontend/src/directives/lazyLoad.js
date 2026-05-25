const lazyLoad = {
  mounted(el, binding) {
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          el.src = binding.value
          observer.unobserve(el)
        }
      })
    }, { rootMargin: '100px' })
    el._lazyObserver = observer
    observer.observe(el)
  },
  unmounted(el) {
    if (el._lazyObserver) {
      el._lazyObserver.unobserve(el)
    }
  }
}

export default {
  install(app) {
    app.directive('lazy-load', lazyLoad)
  }
}
