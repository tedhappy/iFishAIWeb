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
    text: "你能介绍一下AI技术对生活的影响吗？",
  },
  {
    id: "default-productivity-1",
    text: "如何提高我的工作效率和学习能力？",
  },
  {
    id: "default-life-1",
    text: "能分享一些实用的生活小技巧吗？",
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
        text: "如何选择适合初学者的编程语言？",
      },
      {
        id: "coding-practice-1",
        text: "有哪些提高编程技能的实践方法？",
      },
      {
        id: "coding-debug-1",
        text: "如何有效地调试和解决代码问题？",
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
        text: "如何提高我的写作技巧和表达能力？",
      },
      {
        id: "writing-structure-1",
        text: "如何构建清晰的文章结构？",
      },
      {
        id: "writing-creativity-1",
        text: "如何激发写作灵感和创意？",
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
        text: "如何制定有效的商业策略？",
      },
      {
        id: "business-marketing-1",
        text: "有哪些实用的市场营销方法？",
      },
      {
        id: "business-management-1",
        text: "如何提高团队管理效率？",
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
        text: "有哪些高效的学习方法和技巧？",
      },
      {
        id: "education-plan-1",
        text: "如何制定个人学习计划？",
      },
      {
        id: "education-motivation-1",
        text: "如何保持长期的学习动力？",
      },
    ],
    description: "专注于教育、学习和技能发展",
  },
  {
    agentType: "ticket",
    agentName: "门票助手",
    defaultQuestions: [
      {
        id: "ticket-order-1",
        text: "帮我查询最近的门票订单情况",
      },
      {
        id: "ticket-analysis-1",
        text: "能分析一下门票销售数据的趋势吗？",
      },
      {
        id: "ticket-report-1",
        text: "能帮我生成门票订单的统计报表吗？",
      },
    ],
    description: "专注于门票订单查询、数据分析和可视化",
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
