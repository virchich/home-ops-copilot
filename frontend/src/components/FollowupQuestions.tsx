import { useState } from 'react';
import type { FollowupQuestion, FollowupAnswer } from '../types';

interface FollowupQuestionsProps {
  questions: FollowupQuestion[];
  preliminaryAssessment: string | null;
  onSubmit: (answers: FollowupAnswer[]) => void;
  isLoading: boolean;
}

export function FollowupQuestions({
  questions,
  preliminaryAssessment,
  onSubmit,
  isLoading,
}: FollowupQuestionsProps) {
  const [answers, setAnswers] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    questions.forEach((q) => {
      initial[q.id] = '';
    });
    return initial;
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const formattedAnswers: FollowupAnswer[] = questions.map((q) => ({
      question_id: q.id,
      answer: answers[q.id] || 'Not answered',
    }));
    onSubmit(formattedAnswers);
  };

  const updateAnswer = (questionId: string, value: string) => {
    setAnswers((prev) => ({ ...prev, [questionId]: value }));
  };

  const allAnswered = questions.every((q) => answers[q.id]?.trim());

  return (
    <div className="space-y-5">
      {/* Preliminary assessment */}
      {preliminaryAssessment && (
        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <p className="text-sm font-medium text-blue-800 dark:text-blue-300 mb-1">
            Initial Assessment
          </p>
          <p className="text-sm text-blue-700 dark:text-blue-400">{preliminaryAssessment}</p>
        </div>
      )}

      <p className="text-sm text-gray-600 dark:text-gray-400">
        Please answer these questions to help narrow down the issue:
      </p>

      <form onSubmit={handleSubmit} className="space-y-4">
        {questions.map((q, idx) => (
          <div
            key={q.id}
            className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg space-y-2"
          >
            <div className="flex items-start gap-2">
              <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full flex items-center justify-center text-xs font-medium">
                {idx + 1}
              </span>
              <div className="flex-1">
                <p className="text-sm font-medium text-gray-900 dark:text-white">{q.question}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{q.why}</p>
              </div>
            </div>

            {/* Yes/No buttons */}
            {q.question_type === 'yes_no' && (
              <div className="flex gap-2 ml-8">
                {['Yes', 'No', "I'm not sure"].map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => updateAnswer(q.id, option)}
                    className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                      answers[q.id] === option
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                        : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                    }`}
                  >
                    {option}
                  </button>
                ))}
              </div>
            )}

            {/* Multiple choice radios */}
            {q.question_type === 'multiple_choice' && q.options && (
              <div className="space-y-1.5 ml-8">
                {q.options.map((option) => (
                  <label
                    key={option}
                    className={`flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border cursor-pointer transition-colors ${
                      answers[q.id] === option
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                        : 'border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-400 hover:border-gray-300'
                    }`}
                  >
                    <input
                      type="radio"
                      name={q.id}
                      value={option}
                      checked={answers[q.id] === option}
                      onChange={() => updateAnswer(q.id, option)}
                      className="text-blue-600"
                    />
                    {option}
                  </label>
                ))}
              </div>
            )}

            {/* Free text input */}
            {q.question_type === 'free_text' && (
              <div className="ml-8">
                <textarea
                  value={answers[q.id] || ''}
                  onChange={(e) => updateAnswer(q.id, e.target.value)}
                  placeholder="Type your answer..."
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-gray-200 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
                />
              </div>
            )}
          </div>
        ))}

        <button
          type="submit"
          disabled={!allAnswered || isLoading}
          className="w-full px-4 py-2.5 text-sm font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="flex items-center justify-center gap-2">
              <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              Generating diagnosis...
            </span>
          ) : (
            'Get Diagnosis'
          )}
        </button>
      </form>
    </div>
  );
}
