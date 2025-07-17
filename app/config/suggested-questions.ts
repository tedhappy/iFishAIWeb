// 推荐问题配置文件
// 支持不同agent的个性化推荐问题

export interface QuestionConfig {
  id: string; // 问题的唯一标识符，用于缓存管理、点击追踪和去重
  text: string; // 问题的显示文本
}

export interface AgentQuestionsConfig {
  agentType: string;
  agentName: string;
  defaultQuestions: QuestionConfig[];
  description?: string;
}

// 默认通用推荐问题
const DEFAULT_QUESTIONS: QuestionConfig[] = [
  {
    id: "default-ai-1",
    text: "请详细介绍AI技术在教育、医疗、交通三个领域的具体应用和影响",
  },
  {
    id: "default-productivity-1",
    text: "请推荐5个提高工作效率的具体方法，包括时间管理和学习技巧",
  },
  {
    id: "default-life-1",
    text: "分享10个日常生活中实用的小技巧，涵盖健康、整理和省钱方面",
  },
];

// 不同agent的推荐问题配置
export const AGENT_QUESTIONS_CONFIG: AgentQuestionsConfig[] = [
  {
    agentType: "general",
    agentName: "智能伙伴小鱼",
    defaultQuestions: DEFAULT_QUESTIONS,
    description:
      "你的贴心智能伙伴，能聊天解答、搜索信息、查地图路线，就像身边的万能助手！",
  },
  {
    agentType: "coding",
    agentName: "编程助手",
    defaultQuestions: [
      {
        id: "coding-basics-1",
        text: "对比Python、JavaScript、Java三种编程语言的特点，推荐初学者最适合的选择",
      },
      {
        id: "coding-practice-1",
        text: "列出5个提高编程技能的具体实践项目，从简单到复杂逐步进阶",
      },
      {
        id: "coding-debug-1",
        text: "详细说明代码调试的完整流程和5个常用调试技巧，附带实例演示",
      },
    ],
    description: "专注于编程、开发和技术相关问题",
  },
  {
    agentType: "writing",
    agentName: "写作助手",
    defaultQuestions: [
      {
        id: "writing-improve-1",
        text: "提供7个具体的写作技巧来提升文章质量，包括词汇选择、句式变化和逻辑表达",
      },
      {
        id: "writing-structure-1",
        text: "详细介绍议论文、说明文、记叙文三种文体的标准结构模板和写作要点",
      },
      {
        id: "writing-creativity-1",
        text: "分享6种激发写作灵感的实用方法，包括观察技巧、思维导图和素材积累",
      },
    ],
    description: "专注于写作、文案和内容创作",
  },
  {
    agentType: "business",
    agentName: "商业顾问",
    defaultQuestions: [
      {
        id: "business-strategy-1",
        text: "详细介绍SWOT分析法制定商业策略的完整步骤，并提供一个实际案例分析",
      },
      {
        id: "business-marketing-1",
        text: "列出8种低成本高效果的数字营销方法，包括社交媒体、内容营销和SEO策略",
      },
      {
        id: "business-management-1",
        text: "提供团队管理的5个核心原则和10个具体实施技巧，提升团队协作效率",
      },
    ],
    description: "专注于商业、管理和创业相关问题",
  },
  {
    agentType: "education",
    agentName: "教育助手",
    defaultQuestions: [
      {
        id: "education-method-1",
        text: "详细介绍费曼学习法、番茄工作法、间隔重复法等6种科学学习方法的具体操作步骤",
      },
      {
        id: "education-plan-1",
        text: "提供一个完整的个人学习计划模板，包括目标设定、时间分配和进度跟踪方法",
      },
      {
        id: "education-motivation-1",
        text: "分享8个保持长期学习动力的心理技巧和实用方法，克服学习倦怠",
      },
    ],
    description: "专注于教育、学习和技能发展",
  },
  {
    agentType: "chatbi",
    agentName: "ChatBI助手",
    defaultQuestions: [
      {
        id: "chatbi-analysis-1",
        text: "请展示如何使用SQL分析电商平台各省份销售数据，包括查询语句和可视化图表示例",
      },
      {
        id: "chatbi-trend-1",
        text: "演示订单趋势分析的完整流程：从数据提取、清洗到生成趋势图表的具体步骤",
      },
      {
        id: "chatbi-insight-1",
        text: "提供用户画像分析模板：如何按年龄段分析消费行为，包括指标选择和洞察提取方法",
      },
    ],
    description:
      "专业的商业智能数据分析师🐟，擅长SQL查询、数据可视化、商业洞察分析，让数据说话！",
  },
  {
    agentType: "text_to_image",
    agentName: "AI文生图助手",
    defaultQuestions: [
      {
        id: "text-to-image-landscape-1",
        text: "请生成一幅夕阳下的海滩场景：金色沙滩、椰子树剪影、海浪轻拍，动漫风格，色彩温暖",
      },
      {
        id: "text-to-image-character-1",
        text: "创作可爱机器人角色：圆润外形、蓝白配色、大眼睛、友善表情，卡通风格，适合儿童",
      },
      {
        id: "text-to-image-abstract-1",
        text: "设计抽象艺术作品表达快乐：明亮色彩、流动线条、阳光元素、温暖色调，现代艺术风格",
      },
    ],
    description:
      "创意无限的AI绘画师小鱼🐟，能根据你的文字描述生成精美图像，让想象变成现实！",
  },
  {
    agentType: "food_recommendation",
    agentName: "美食推荐助手",
    defaultQuestions: [
      {
        id: "food-local-1",
        text: "推荐北京5家适合商务宴请的川菜餐厅，包括地址、人均消费、特色菜品和预订方式",
      },
      {
        id: "food-romantic-1",
        text: "推荐3家适合约会的浪漫西餐厅，人均200元以内，包括环境特色、推荐菜品和最佳座位",
      },
      {
        id: "food-gathering-1",
        text: "推荐4家适合朋友聚会的热闹火锅店，包括特色锅底、聚会包间、停车信息和团购优惠",
      },
    ],
    description:
      "贴心的美食向导小鱼🐟，精通各地美食文化，为你推荐最适合的餐厅和美味！",
  },
  {
    agentType: "train_ticket",
    agentName: "火车票查询助手",
    defaultQuestions: [
      {
        id: "train-ticket-query-1",
        text: "查询今日北京到上海的所有高铁班次，显示发车时间、到达时间、历时和票价信息",
      },
      {
        id: "train-ticket-schedule-1",
        text: "提供G1次列车的完整时刻表，包括所有停靠站点、到发时间和停车时长",
      },
      {
        id: "train-ticket-station-1",
        text: "查询北京南站今日所有出发车次，按时间排序显示目的地、车次号和余票情况",
      },
    ],
    description:
      "专业的火车票查询助手🚄，基于12306官方数据，为您提供准确可靠的火车出行信息！",
  },
  {
    agentType: "fortune_teller",
    agentName: "算命先生",
    defaultQuestions: [
      {
        id: "fortune-teller-bazi-1",
        text: "详细解释八字命理的基本原理，包括天干地支、五行相生相克和命盘分析方法",
      },
      {
        id: "fortune-teller-career-1",
        text: "分析不同五行属性的人适合的职业方向，以及如何根据八字选择最佳发展时机",
      },
      {
        id: "fortune-teller-love-1",
        text: "解读传统命理中的桃花运概念，包括桃花星的含义和如何通过八字看婚姻缘分",
      },
    ],
    description:
      "精通传统命理学的算命先生🔮，擅长八字分析、运势预测，为您指点人生迷津！",
  },
];

// 根据agent类型获取推荐问题
export function getQuestionsByAgentType(agentType?: string): QuestionConfig[] {
  if (!agentType) {
    return DEFAULT_QUESTIONS;
  }

  const config = AGENT_QUESTIONS_CONFIG.find(
    (config) => config.agentType === agentType,
  );
  return config ? config.defaultQuestions : DEFAULT_QUESTIONS;
}

// 获取所有可用的agent类型
export function getAvailableAgentTypes(): string[] {
  return AGENT_QUESTIONS_CONFIG.map((config) => config.agentType);
}

// 根据agent类型获取agent名称
export function getAgentName(agentType?: string): string {
  if (!agentType) {
    return "智能伙伴小鱼";
  }

  const config = AGENT_QUESTIONS_CONFIG.find(
    (config) => config.agentType === agentType,
  );
  return config ? config.agentName : "智能伙伴小鱼";
}

// 获取agent描述
export function getAgentDescription(agentType?: string): string {
  if (!agentType) {
    return "你的贴心智能伙伴，能聊天解答、搜索信息、查地图路线，就像身边的万能助手！";
  }

  const config = AGENT_QUESTIONS_CONFIG.find(
    (config) => config.agentType === agentType,
  );
  return config
    ? config.description || ""
    : "你的贴心智能伙伴，能聊天解答、搜索信息、查地图路线，就像身边的万能助手！";
}

// 验证问题配置的有效性
export function validateQuestionConfig(config: AgentQuestionsConfig): boolean {
  if (!config.agentType || !config.agentName || !config.defaultQuestions) {
    return false;
  }

  if (
    !Array.isArray(config.defaultQuestions) ||
    config.defaultQuestions.length === 0
  ) {
    return false;
  }

  return config.defaultQuestions.every(
    (q) => q.id && q.text && q.text.trim().length > 0,
  );
}
