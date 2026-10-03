<!-- Profile：个人中心页，只负责组合头像卡、侧边列表、修改密码三个零件。 -->
<template>
  <div class="profile">
    <h1>个人中心</h1>

    <AvatarCard />
    <SideLists />
    <PasswordForm />
  </div>
</template>

<script setup>
import AvatarCard from '@/components/profile/AvatarCard.vue'
import PasswordForm from '@/components/profile/PasswordForm.vue'
import SideLists from '@/components/profile/SideLists.vue'
</script>

<style scoped>
.profile { max-width: 720px; margin: 0 auto; }
h1 { font-size: 26px; margin-bottom: 20px; }
</style>
