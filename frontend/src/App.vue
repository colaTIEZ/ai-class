<script setup lang="ts">
// Main application layout
</script>

<template>
  <div class="app-wrapper w-full min-h-screen bg-slate-50 font-sans text-slate-800">
    <!-- Navbar placeholder for AI-Class -->
    <header class="w-full h-16 bg-white border-b border-slate-200 shadow-sm flex items-center px-6 fixed top-0 z-50">
      <div class="logo font-bold text-xl text-indigo-600 tracking-tight">AI-Class</div>
      <nav class="ml-8 space-x-4 text-sm font-medium text-slate-600">
        <router-link to="/" class="hover:text-indigo-600 transition-colors">Study Material</router-link>
        <span class="text-slate-300">|</span>
        <span class="text-slate-400 cursor-not-allowed">Review Notebook (Epic 3)</span>
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
</style>
