import { createRouter, createWebHistory } from 'vue-router'
import SearchView from '../views/trace/SearchView.vue'
import PathView from '../views/trace/PathView.vue'
import EventView from '../views/trace/EventView.vue'
import RiskView from '../views/fake-know/RiskView.vue'
import FakeView from '../views/fake-know/FakeView.vue'
import BadView from '../views/fake-know/BadView.vue'
import DashboardView from '../views/dashboard/DashboardView.vue'

const routes = [
  {
    path: '/',
    name: 'Search',
    component: SearchView
  },
  {
    path: '/trace',
    name: 'Trace',
    component: SearchView
  },
  {
    path: '/path',
    name: 'Path',
    component: PathView,
    props: route => ({ 
      initialGraphId: route.query.id,
      initialGraphEvent: route.query.event 
    })
  },
  {
    path: '/event',
    name: 'Event',
    component: EventView
  },
  {
    path: '/risk',
    name: 'Risk',
    component: RiskView
  },
  {
    path: '/fake',
    name: 'Fake',
    component: FakeView
  },
  {
    path: '/bad',
    name: 'Bad',
    component: BadView
  },
  {
    path: '/dashboard',
    name: 'Dashboard',
    component: DashboardView
  }
]

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
})

export default router