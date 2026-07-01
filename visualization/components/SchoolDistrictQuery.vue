<template>
  <div class="school-district-query">
    <div class="query-header">
      <h3>学区查询</h3>
      <p class="subtitle">数据来源：浙里办「入学早知道」</p>
    </div>

    <!-- 搜索区域 -->
    <div class="search-area">
      <div class="search-tabs">
        <span
          :class="['tab', { active: searchMode === 'community' }]"
          @click="searchMode = 'community'"
        >按小区查学校</span>
        <span
          :class="['tab', { active: searchMode === 'school' }]"
          @click="searchMode = 'school'"
        >按学校查小区</span>
      </div>

      <div class="search-input">
        <el-input
          v-model="keyword"
          :placeholder="searchMode === 'community' ? '输入小区名称...' : '输入学校名称...'"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 区域筛选 -->
      <div class="district-filter">
        <el-select v-model="selectedDistrict" placeholder="选择区域" clearable>
          <el-option
            v-for="d in districts"
            :key="d"
            :label="d"
            :value="d"
          />
        </el-select>
      </div>
    </div>

    <!-- 查询结果 -->
    <div class="result-area">
      <div v-if="loading" class="loading">加载中...</div>

      <div v-else-if="results.length > 0" class="result-list">
        <div
          v-for="(item, index) in results"
          :key="index"
          class="result-card"
        >
          <div class="card-header">
            <span class="school-name">{{ item.school_name }}</span>
            <el-tag :type="getLevelTagType(item.school_level)" size="small">
              {{ item.school_level }}
            </el-tag>
          </div>
          <div class="card-body">
            <div class="info-row">
              <span class="label">学段：</span>
              <span>{{ item.school_type }}</span>
            </div>
            <div class="info-row">
              <span class="label">所属区：</span>
              <span>{{ item.district }}</span>
            </div>
            <div class="info-row">
              <span class="label">对口小区：</span>
              <span class="community">{{ item.community_name }}</span>
            </div>
            <div v-if="item.avg_price" class="info-row price-row">
              <span class="label">小区均价：</span>
              <span class="price">{{ item.avg_price }} 元/㎡</span>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty">
        <p>暂无匹配结果</p>
        <p class="tip">试试搜索「学军」或「求智」</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// ============================================================
// 类型定义
// ============================================================

interface SchoolCommunityItem {
  school_name: string
  school_level: string
  school_type: string
  district: string
  community_name: string
  enrollment_year: number
  avg_price?: number
}

// ============================================================
// 状态
// ============================================================

const searchMode = ref<'community' | 'school'>('community')
const keyword = ref('')
const selectedDistrict = ref('')
const loading = ref(false)
const results = ref<SchoolCommunityItem[]>([])

const districts = [
  '上城区', '拱墅区', '西湖区', '滨江区',
  '余杭区', '萧山区', '临平区', '钱塘区'
]

// ============================================================
// 方法
// ============================================================

function handleSearch() {
  if (!keyword.value.trim()) {
    results.value = []
    return
  }

  loading.value = true

  // TODO: 对接真实数据集 API
  setTimeout(() => {
    results.value = mockSearch(keyword.value, searchMode.value, selectedDistrict.value)
    loading.value = false
  }, 300)
}

function mockSearch(
  kw: string,
  mode: 'community' | 'school',
  district: string
): SchoolCommunityItem[] {
  const mockData: SchoolCommunityItem[] = [
    { school_name: '杭州市学军小学(求智校区)', school_level: '省重点', school_type: '小学', district: '西湖区', community_name: '求智社区', enrollment_year: 2025, avg_price: 85000 },
    { school_name: '杭州市学军小学(求智校区)', school_level: '省重点', school_type: '小学', district: '西湖区', community_name: '文三新村', enrollment_year: 2025, avg_price: 72000 },
    { school_name: '杭州市天长小学', school_level: '省重点', school_type: '小学', district: '上城区', community_name: '岳王路社区', enrollment_year: 2025, avg_price: 78000 },
    { school_name: '杭州市胜利小学', school_level: '省重点', school_type: '小学', district: '上城区', community_name: '近江社区', enrollment_year: 2025, avg_price: 62000 },
    { school_name: '杭州江南实验学校', school_level: '市重点', school_type: '九年一贯制', district: '滨江区', community_name: '月明社区', enrollment_year: 2025, avg_price: 55000 },
  ]

  return mockData.filter(item => {
    const matchKeyword = mode === 'school'
      ? item.school_name.includes(kw)
      : item.community_name.includes(kw)
    const matchDistrict = !district || item.district === district
    return matchKeyword && matchDistrict
  })
}

function getLevelTagType(level: string): string {
  const map: Record<string, string> = {
    '省重点': 'danger',
    '市重点': 'warning',
    '区重点': 'info',
    '普通': '',
  }
  return map[level] || ''
}
</script>

<style scoped lang="scss">
.school-district-query {
  padding: 20px;
  background: #fff;
  border-radius: 16px;
  box-shadow: 0px 2px 12px 0px rgba(0, 0, 0, 0.10);
}

.query-header {
  margin-bottom: 20px;

  h3 {
    font-size: 20px;
    font-weight: bold;
    margin: 0 0 4px;
  }

  .subtitle {
    font-size: 12px;
    color: #999;
    margin: 0;
  }
}

.search-area {
  margin-bottom: 20px;

  .search-tabs {
    display: flex;
    gap: 16px;
    margin-bottom: 12px;

    .tab {
      font-size: 14px;
      color: #666;
      cursor: pointer;
      padding-bottom: 4px;

      &.active {
        color: #0A8754;
        border-bottom: 2px solid #0A8754;
        font-weight: bold;
      }
    }
  }

  .search-input {
    margin-bottom: 12px;
  }
}

.result-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  padding: 16px;
  background: #f7f8fa;
  border-radius: 8px;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0px 2px 6px 0px rgba(0, 0, 0, 0.08);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;

    .school-name {
      font-size: 16px;
      font-weight: bold;
    }
  }

  .card-body {
    .info-row {
      font-size: 14px;
      line-height: 28px;

      .label {
        color: #999;
      }

      .community {
        color: #0A8754;
        font-weight: 500;
      }
    }

    .price-row .price {
      color: #f5222d;
      font-weight: bold;
    }
  }
}

.empty {
  text-align: center;
  padding: 40px 0;
  color: #999;

  .tip {
    font-size: 12px;
    margin-top: 8px;
  }
}

.loading {
  text-align: center;
  padding: 40px 0;
  color: #666;
}
</style>
