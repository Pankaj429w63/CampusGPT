
export interface AskRequest {
  question: string;
}

export interface AskResponse {
  status: string;
  question: string;
  answer: string;
  sources: unknown[];
}

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/+$/, "") ||
  "http://localhost:8000";

export async function askCampusGPT(
  question: string
): Promise<AskResponse> {
  const trimmedQuestion = question.trim();

  if (!trimmedQuestion) {
    throw new Error("Please enter a question.");
  }

  let response: Response;

  try {
    response = await fetch(`${API_BASE_URL}/ask`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: trimmedQuestion,
      }),
    });
  } catch {
    throw new Error(
      "Cannot connect to CampusGPT. Please check that the backend is running."
    );
  }

  if (!response.ok) {
    throw new Error(
      `CampusGPT server returned an error (${response.status}).`
    );
  }

  let data: unknown;

  try {
    data = await response.json();
  } catch {
    throw new Error("CampusGPT returned an invalid response.");
  }

  if (
    typeof data !== "object" ||
    data === null ||
    !("answer" in data) ||
    typeof data.answer !== "string"
  ) {
    throw new Error("The backend response format is invalid.");
  }

  return {
    status: "status" in data && typeof data.status === "string"
      ? data.status
      : "success",
    question: "question" in data && typeof data.question === "string"
      ? data.question
      : trimmedQuestion,
    answer: data.answer,
    sources: "sources" in data && Array.isArray(data.sources)
      ? data.sources
      : [],
  };
}
