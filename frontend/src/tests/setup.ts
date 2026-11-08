import '@testing-library/jest-dom/vitest'

// jsdom não implementa IntersectionObserver; motion/react precisa dele para
// whileInView. Um stub inerte basta nos testes — nenhum deles depende da
// animação realmente disparar.
class IntersectionObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords(): IntersectionObserverEntry[] {
    return []
  }
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any -- stub de teste, não o contrato real da API
;(globalThis as any).IntersectionObserver = IntersectionObserverStub
