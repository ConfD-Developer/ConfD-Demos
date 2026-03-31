<template>
  <TooltipNeedTransaction>
    <q-item
      clickable
      dense
      ripple
      :disable="isDisabled()"
      :active="isActive"
      class="q-py-sm"
      active-class="bg-blue-2 text-grey-8"
      @click="doActivate"
    >
      <q-item-section>
        <q-item-label>
          <q-badge :color="badgeColor()">
            {{ modelData.name }}
          </q-badge>
        </q-item-label>
        <q-item-label
          caption
          lines="1"
        >
          {{ namespace }}
        </q-item-label>
      </q-item-section>
    </q-item>
  </TooltipNeedTransaction>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { storeToRefs } from 'pinia'
import { useModelsStore } from 'src/stores/models'
import { useServerStore } from 'src/stores/server'
import { useTransactionStore } from 'src/stores/transaction'
import TooltipNeedTransaction from 'components/helpers/TooltipNeedTransaction.vue'

const props = defineProps<{ namespace: string }>()

const modelsStore = useModelsStore()
const txStore = useTransactionStore()
const { tasks } = storeToRefs(useServerStore())
const { activeNamespace, loadedModels } = storeToRefs(modelsStore)

const isActive = computed(() => activeNamespace.value === props.namespace)
const modelData = computed(() => loadedModels.value[props.namespace])
const { hasTrans } = storeToRefs(txStore)

const isDisabled = () => !hasTrans.value
const badgeColor = () => (isDisabled() ? 'grey' : 'primary')

const doActivate = () => tasks.value?.models.activateModel(props.namespace)
</script>
