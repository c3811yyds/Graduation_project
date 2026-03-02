import { createRouter, createWebHistory } from "vue-router";
import HomeView from "../views/HomeView.vue";
import CourseDetailView from "../views/CourseDetailView.vue";
import DashboardView from "../views/DashboardView.vue";
import ProfileView from "../views/ProfileView.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: "/",
      name: "home",
      component: HomeView,
    },
    {
      path: "/courses/:id",
      name: "course-detail",
      component: CourseDetailView,
      props: true,
    },
    {
      path: "/dashboard",
      name: "dashboard",
      component: DashboardView,
    },
    {
      path: "/profile",
      name: "profile",
      component: ProfileView,
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/",
    },
  ],
});

export default router;