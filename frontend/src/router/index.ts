import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      redirect: '/documents/1', // default mock route for current epic testing
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
