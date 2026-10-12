<script setup>
import { computed, ref, watch } from "vue";
const props = defineProps({ images: Array, open: Boolean, selected: String });
const emit = defineEmits(["update:open", "select"]);
const picks = ref([]);
watch(
  () => props.open,
  (value) => {
    if (value) picks.value = props.images.slice(-2).map((a) => a.id);
  },
);
const compared = computed(() =>
  props.images.filter((a) => picks.value.includes(a.id)),
);
</script>
<template>
  <el-dialog
    :model-value="open"
    title="比较图片"
    width="85%"
    @update:model-value="emit('update:open', $event)"
    ><el-select
      v-model="picks"
      multiple
      :multiple-limit="4"
      placeholder="选择 2–4 张图片"
      ><el-option
        v-for="(image, index) in images"
        :key="image.id"
        :value="image.id"
        :label="`图片 ${index + 1}`"
    /></el-select>
    <div
      class="compare-grid"
      :style="{
        gridTemplateColumns: `repeat(${Math.max(compared.length, 1)}, minmax(0, 1fr))`,
      }"
    >
      <div v-for="image in compared" :key="image.id" class="compare-item">
        <img :src="image.url" alt="比较图片" />
        <div>
          <span>{{ image.width }} × {{ image.height }}</span
          ><el-button
            :type="selected === image.id ? 'success' : 'primary'"
            plain
            size="small"
            @click="emit('select', image.id)"
            >{{ selected === image.id ? "已选中" : "选用这张" }}</el-button
          >
        </div>
      </div>
    </div></el-dialog
  >
</template>
<style scoped>
.compare-grid {
  display: grid;
  gap: 18px;
  margin-top: 22px;
}
.compare-item img {
  width: 100%;
  height: 50vh;
  object-fit: contain;
  background: #f5f7f5;
  border-radius: 8px;
}
.compare-item > div {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  font-size: 12px;
  color: #86948b;
}
</style>
