<script setup lang="ts">
// Main application layout
</script>

<template>
  <div class="app-wrapper w-full min-h-screen bg-slate-50 font-sans text-slate-800">
    <!-- Navbar placeholder for AI-Class -->
    <header class="w-full h-16 bg-white/70 backdrop-blur-xl border-b border-indigo-100/50 shadow-[0_4px_30px_rgba(0,0,0,0.03)] flex items-center px-8 fixed top-0 z-50 transition-all">
      <div class="logo font-black text-2xl tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-indigo-500 to-purple-600 hover:from-purple-500 hover:to-orange-500 transition-all cursor-default select-none animate-[pulse_4s_ease-in-out_infinite]">
        AI-Class
      </div>
      <nav class="ml-10 flex h-full items-center gap-6 text-sm font-bold text-slate-500">
        <router-link to="/upload" class="nav-link relative h-full flex items-center px-2 hover:text-indigo-600 transition-colors">
          <span class="z-10 tracking-widest">📜 解读卷轴</span>
          <div class="nav-indicator absolute bottom-0 left-0 h-1 w-full scale-x-0 rounded-t-md bg-indigo-500 transition-transform origin-center"></div>
        </router-link>
        <span class="h-4 w-px bg-slate-200"></span>
        <router-link to="/documents" class="nav-link relative h-full flex items-center px-2 hover:text-indigo-600 transition-colors">
          <span class="z-10 tracking-widest">🔮 知识领地</span>
          <div class="nav-indicator absolute bottom-0 left-0 h-1 w-full scale-x-0 rounded-t-md bg-indigo-500 transition-transform origin-center"></div>
        </router-link>
        <span class="h-4 w-px bg-slate-200"></span>
        <router-link to="/review" class="nav-link relative h-full flex items-center px-2 hover:text-indigo-600 transition-colors">
          <span class="z-10 tracking-widest">👾 小怪兽图鉴</span>
          <div class="nav-indicator absolute bottom-0 left-0 h-1 w-full scale-x-0 rounded-t-md bg-indigo-500 transition-transform origin-center"></div>
        </router-link>
      </nav>
    </header>
    
    <main class="w-full pt-16 min-h-screen">
      <router-view />
    </main>
  </div>
</template>

<style>
/* Global resets or additions */
body {
  margin: 0;
  padding: 0;
  -webkit-font-smoothing: antialiased;
}

/* Base router active class for nav styling */
.router-link-active {
  color: #4f46e5; /* indigo-600 */
}
.router-link-active .nav-indicator {
  transform: scaleX(1);
}
.nav-link:hover .nav-indicator {
  transform: scaleX(0.8);
}
</style>
