import {
  RES_FORMAT,
  RES_FORMAT_MATCH_COLUMNS,
  RES_FORMAT_MULTI_SELECT,
  SYSTEM_PROMPT_TEMPLATE,
  SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS,
  USER_PROMPT_MATCHING_PER_DIFFICULTY,
  USER_PROMPT_PER_DIFFICULTY,
  USER_PROMPT_TEMPLATE,
  USER_PROMPT_TEMPLATE_MATCH_COLUMNS,
} from "./prompts";
import {
  Difficulty,
  FormatConversionInput,
  GenerateQuestionInput,
  GeneratedQuestion,
  LevelOfQuiz,
  McqQuestion,
  MatchingQuestion,
  PromptBatchRequest,
  PromptPayload,
  PromptRequest,
  QuestionType,
  QualityCheck,
  ReqFormattedQuestion,
} from "./dto/question-types";

export class QuestionsService {
  generateQuestion(input: GenerateQuestionInput): {
    question: GeneratedQuestion;
    quality: QualityCheck;
  } {
    const topic = (input.topic || "the topic").trim();
    const stem =
      (input.stem && input.stem.trim()) ||
      `Which statement best describes ${topic}?`;
    const answer = (input.answer || topic).trim();
    const difficulty: Difficulty = input.difficulty || "medium";

    const distractors = this.ensureDistractors(
      answer,
      input.distractors || [],
      topic
    );
    const choices = this.shuffle([answer, ...distractors]);
    const question: GeneratedQuestion = {
      topic,
      stem: this.ensureQuestionMark(stem),
      answer,
      distractors,
      choices,
      difficulty,
    };

    const quality = this.checkQuality(question);
    if (!quality.isPassing) {
      const improvedDistractors = this.ensureDistractors(
        answer,
        question.distractors,
        topic,
        true
      );
      question.distractors = improvedDistractors;
      question.choices = this.shuffle([answer, ...improvedDistractors]);
    }

    return { question, quality: this.checkQuality(question) };
  }

  checkQuality(question: GeneratedQuestion): QualityCheck {
    const issues: string[] = [];
    const suggestions: string[] = [];
    let score = 100;
    const distractors = question.distractors || [];
    const choices =
      question.choices && question.choices.length > 0
        ? question.choices
        : [question.answer, ...distractors];

    if (question.stem.length < 15) {
      score -= 20;
      issues.push("Stem is too short.");
      suggestions.push("Make the question stem more descriptive.");
    }

    if (question.stem.toLowerCase().includes(question.answer.toLowerCase())) {
      score -= 25;
      issues.push("Answer appears in the stem.");
      suggestions.push("Remove the answer from the stem.");
    }

    if (distractors.length < 3) {
      score -= 20;
      issues.push("Not enough distractors.");
      suggestions.push("Provide at least three distractors.");
    }

    const uniqueChoices = new Set(choices.map((c) => c.toLowerCase()));
    if (uniqueChoices.size !== choices.length) {
      score -= 15;
      issues.push("Duplicate choices detected.");
      suggestions.push("Ensure all choices are unique.");
    }

    if (question.answer.trim().length < 3) {
      score -= 10;
      issues.push("Answer is too short.");
      suggestions.push("Provide a more specific answer.");
    }

    if (score < 0) {
      score = 0;
    }

    return {
      score,
      isPassing: score >= 70,
      issues,
      suggestions,
    };
  }

  toReqFormat(question: GeneratedQuestion, quality: QualityCheck): ReqFormattedQuestion {
    return {
      metadata: {
        difficulty: question.difficulty,
        qualityScore: quality.score,
      },
      question: {
        id: this.slugify(`${question.topic}-${Date.now()}`),
        stem: question.stem,
        options: question.choices,
        answer: question.answer,
      },
    };
  }

  buildPromptPayload(input: PromptRequest): PromptPayload {
    const locale = input.locale || "en";
    const sourceText = input.sourceText || "";
    const learningObj = input.learningObjectives.join(" | ");
    const numberOfQuestions = input.numberOfQuestions || 3;
    const questionType: QuestionType =
      input.questionType || "MULTIPLE_CHOICE";
    const perDifficulty = input.perDifficulty || false;
    const numCorrectOptions = input.numCorrectOptions || 1;
    const numIncorrectOptions = input.numIncorrectOptions || 3;

    if (questionType === "MATCHING") {
      const systemPrompt = SYSTEM_PROMPT_TEMPLATE_MATCH_COLUMNS.replace(
        "{locale}",
        locale
      );
      const userPrompt = perDifficulty
        ? USER_PROMPT_MATCHING_PER_DIFFICULTY.replace(
            "{difficulty_level}",
            input.difficultyLevel || "Beginner"
          )
            .replace("{source_text}", sourceText)
            .replace("{learning_obj}", learningObj)
            .replace("{number_of_questions}", String(numberOfQuestions))
            .replace("{res_format}", RES_FORMAT_MATCH_COLUMNS)
        : USER_PROMPT_TEMPLATE_MATCH_COLUMNS.replace(
            "{source_text}",
            sourceText
          )
            .replace("{learning_obj}", learningObj)
            .replace("{number_of_questions}", String(numberOfQuestions))
            .replace("{res_format_match_columns}", RES_FORMAT_MATCH_COLUMNS);

      return {
        systemPrompt,
        userPrompt,
        responseFormat: RES_FORMAT_MATCH_COLUMNS,
        learningObjective: learningObj,
        difficultyLevel: perDifficulty
          ? input.difficultyLevel || "Beginner"
          : undefined,
        questionType,
      };
    }

    const responseFormat =
      questionType === "MULTIPLE_CHOICE_MULTI_SELECT"
        ? RES_FORMAT_MULTI_SELECT
        : RES_FORMAT;
    const systemPrompt = SYSTEM_PROMPT_TEMPLATE.replace("{locale}", locale)
      .replace("{num_correct_options}", String(numCorrectOptions))
      .replace("{num_incorrect_options}", String(numIncorrectOptions));
    const userPrompt = perDifficulty
      ? USER_PROMPT_PER_DIFFICULTY.replace(
          "{difficulty_level}",
          input.difficultyLevel || "Beginner"
        )
          .replace("{source_text}", sourceText)
          .replace("{learning_obj}", learningObj)
          .replace("{number_of_questions}", String(numberOfQuestions))
          .replace("{res_format}", responseFormat)
      : USER_PROMPT_TEMPLATE.replace("{source_text}", sourceText)
          .replace("{learning_obj}", learningObj)
          .replace("{number_of_questions}", String(numberOfQuestions))
          .replace("{res_format}", responseFormat);

    return {
      systemPrompt,
      userPrompt,
      responseFormat,
      learningObjective: learningObj,
      difficultyLevel: perDifficulty
        ? input.difficultyLevel || "Beginner"
        : undefined,
      questionType,
    };
  }

  toResponseFormat(input: FormatConversionInput) {
    const level = input.levelOfQuiz;
    if (input.questionType === "MATCHING") {
      return [
        {
          LearningObjective: input.learningObjective,
          LevelOfQuiz: level,
          questions: input.questions as MatchingQuestion[],
        },
      ];
    }

    return [
      {
        LearningObjective: input.learningObjective,
        LevelOfQuiz: level,
        questions: input.questions as McqQuestion[],
      },
    ];
  }

  buildPromptBatch(input: PromptBatchRequest): PromptPayload[] {
    const questionTypes: QuestionType[] = input.questionTypes.length
      ? input.questionTypes
      : ["MULTIPLE_CHOICE"];
    const difficulties: LevelOfQuiz[] = [
      "Beginner",
      "Intermediate",
      "Advanced",
    ];

    const payloads: PromptPayload[] = [];
    for (const learningObjective of input.learningObjectives) {
      for (const questionType of questionTypes) {
        for (const difficultyLevel of difficulties) {
          payloads.push(
            this.buildPromptPayload({
              locale: input.locale,
              sourceText: input.sourceText,
              learningObjectives: [learningObjective],
              numberOfQuestions: input.numberOfQuestions,
              difficultyLevel,
              questionType,
              perDifficulty: true,
              numCorrectOptions: input.numCorrectOptions,
              numIncorrectOptions: input.numIncorrectOptions,
            })
          );
        }
      }
    }

    return payloads;
  }

  private ensureDistractors(
    answer: string,
    inputDistractors: string[],
    topic: string,
    forceMore = false
  ): string[] {
    const normalizedAnswer = answer.trim().toLowerCase();
    const distractors = inputDistractors
      .map((d) => d.trim())
      .filter((d) => d && d.toLowerCase() !== normalizedAnswer);

    const needsMore =
      forceMore ||
      distractors.length < 3 ||
      this.isTooEasy(answer, distractors);

    if (needsMore) {
      const fallback = this.generateFallbackDistractors(topic, answer);
      for (const item of fallback) {
        if (distractors.length >= 4) break;
        if (!distractors.some((d) => d.toLowerCase() === item.toLowerCase())) {
          distractors.push(item);
        }
      }
    }

    return distractors.slice(0, 4);
  }

  private isTooEasy(answer: string, distractors: string[]): boolean {
    if (distractors.length < 3) return true;
    if (answer.length <= 3) return true;
    const answerPrefix = answer.slice(0, 3).toLowerCase();
    return distractors.every(
      (d) => d.slice(0, 3).toLowerCase() !== answerPrefix
    );
  }

  private generateFallbackDistractors(topic: string, answer: string): string[] {
    const safeTopic = topic || "the topic";
    return [
      `An unrelated detail about ${safeTopic}`,
      `A common misconception about ${safeTopic}`,
      `An opposite idea to ${answer}`,
      `A less specific example of ${safeTopic}`,
      `A partially correct statement about ${safeTopic}`,
    ];
  }

  private ensureQuestionMark(stem: string): string {
    return stem.trim().endsWith("?") ? stem.trim() : `${stem.trim()}?`;
  }

  private shuffle<T>(values: T[]): T[] {
    const copy = [...values];
    for (let i = copy.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [copy[i], copy[j]] = [copy[j], copy[i]];
    }
    return copy;
  }

  private slugify(value: string): string {
    return value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/(^-|-$)+/g, "");
  }
}
