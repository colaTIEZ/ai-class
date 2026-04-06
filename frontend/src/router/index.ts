import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/upload',
    },
    {
      path: '/upload',
      name: 'upload',
      component: () => import('../views/UploadView.vue'),
    },
    {
      path: '/documents',
      name: 'documents-entry',
      component: () => import('../views/DocumentsEntryView.vue'),
    },
    {
      path: '/documents/:id',
      name: 'document-view',
      component: () => import('../views/DocumentView.vue'),
    },
    {
      path: '/quiz',
      name: 'quiz',
      component: () => import('../views/QuizView.vue'),
    },
    {
      path: '/review',
      name: 'review',
      component: () => import('../views/ReviewPage.vue'),
    }
  ]
})

export default router
