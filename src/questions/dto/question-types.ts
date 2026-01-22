export type Difficulty = "easy" | "medium" | "hard";
export type LevelOfQuiz = "Beginner" | "Intermediate" | "Advanced";
export type QuestionType =
  | "MULTIPLE_CHOICE"
  | "MULTIPLE_CHOICE_MULTI_SELECT"
  | "MATCHING";

export type GenerateQuestionInput = {
  topic?: string;
  stem?: string;
  answer?: string;
  distractors?: string[];
  difficulty?: Difficulty;
};

export type GeneratedQuestion = {
  topic: string;
  stem: string;
  answer: string;
  distractors: string[];
  choices: string[];
  difficulty: Difficulty;
};

export type QualityCheck = {
  score: number;
  isPassing: boolean;
  issues: string[];
  suggestions: string[];
};

export type ReqFormattedQuestion = {
  metadata: {
    difficulty: Difficulty;
    qualityScore: number;
  };
  question: {
    id: string;
    stem: string;
    options: string[];
    answer: string;
  };
};

export type PromptRequest = {
  locale?: string;
  sourceText?: string;
  learningObjectives: string[];
  numberOfQuestions?: number;
  difficultyLevel?: LevelOfQuiz;
  questionType?: QuestionType;
  perDifficulty?: boolean;
  numCorrectOptions?: number;
  numIncorrectOptions?: number;
};

export type PromptPayload = {
  systemPrompt: string;
  userPrompt: string;
  responseFormat: string;
  learningObjective: string;
  difficultyLevel?: LevelOfQuiz;
  questionType: QuestionType;
};

export type PromptBatchRequest = {
  locale?: string;
  sourceText?: string;
  learningObjectives: string[];
  numberOfQuestions?: number;
  questionTypes: QuestionType[];
  numCorrectOptions?: number;
  numIncorrectOptions?: number;
};

export type McqAnswer = {
  answer: string;
  explanation: string;
  correct: boolean;
};

export type McqQuestion = {
  question: string;
  answers: McqAnswer[];
};

export type MatchingAnswer = {
  column_a_answers: string;
  column_b_answers: string;
  explanation: string;
};

export type MatchingQuestion = {
  question: string;
  column_a_answers: Array<Record<string, string>>;
  column_b_answers: Array<Record<string, string>>;
  answers: MatchingAnswer[];
};

export type FormatConversionInput = {
  learningObjective: string;
  levelOfQuiz: LevelOfQuiz;
  questionType: QuestionType;
  questions:
    | McqQuestion[]
    | MatchingQuestion[]
    | Array<Record<string, unknown>>;
};
