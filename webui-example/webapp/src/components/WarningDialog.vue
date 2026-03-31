<template>
  <q-dialog
    v-model="isDialogOn"
    persistent
  >
    <q-card>
      <q-card-section class="q-gutter-y-md">
        <div class="text-h4">
          Beware!
        </div>
        <q-separator />
        <div class="text-h6 q-gutter-y-md">
          Please note that that this is by no means an official replacement
          of deprecated WEB-UI of ConfD, neither production ready product!
          It may not include important parts of proper WEB-UI.
          <q-separator />
          It is an example on how you can implement (parts of) new own solution
          tailored and adjusted to your specific web app needs and conditions.
          <q-separator />
          You can take inspiration in some of the concepts used here,
          but please note that this is not a product - there is no support,
          features roadmap, etc.
        </div>
      </q-card-section>

      <q-card-actions align="right">
        <q-btn
          v-close-popup
          no-caps
          label="Ok, I understand"
        />
      </q-card-actions>
    </q-card>
  </q-dialog>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const isDialogOn = ref(true)
</script>
