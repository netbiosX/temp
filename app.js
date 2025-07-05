import React, { useState, useEffect } from "react";
import jsPDF from "jspdf";

const QUESTIONS = [
  {
    question: "What is the main goal of a Purple Team?",
    options: [
      "To detect phishing emails",
      "To align Red and Blue team efforts for better security",
      "To conduct only penetration testing",
      "To only monitor SIEM alerts"
    ],
    answer: 1,
  },
  {
    question: "Which color is often associated with Purple Teaming?",
    options: [
      "Blue",
      "Red",
      "Purple",
      "Green"
    ],
    answer: 2,
  },
  // Add more questions as needed
];

const PASS_MARK = 75;
const EXAM_TIME_SECONDS = 60 * 2; // 2 minutes for demo

function App() {
  const [name, setName] = useState("");
  const [started, setStarted] = useState(false);
  const [answers, setAnswers] = useState(Array(QUESTIONS.length).fill(null));
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(EXAM_TIME_SECONDS);

  // Timer effect
  useEffect(() => {
    if (!started || submitted) return;
    if (timeLeft === 0) {
      handleSubmit();
      return;
    }
    const timer = setInterval(() => setTimeLeft(t => t - 1), 1000);
    return () => clearInterval(timer);
  }, [started, timeLeft, submitted]);

  const handleOptionChange = (qIdx, oIdx) => {
    const newAnswers = [...answers];
    newAnswers[qIdx] = oIdx;
    setAnswers(newAnswers);
  };

  const handleSubmit = () => {
    let correct = 0;
    answers.forEach((a, i) => {
      if (a === QUESTIONS[i].answer) correct++;
    });
    setScore(correct);
    setSubmitted(true);
    setStarted(false);
    setTimeLeft(0);
    setTimeout(() => exportResults(correct), 1200);
  };

  const exportResults = (correct) => {
    const percentage = ((correct / QUESTIONS.length) * 100).toFixed(2);
    const result = percentage >= PASS_MARK ? "PASS" : "FAIL";
    const txt = `Name: ${name}
Score: ${correct} / ${QUESTIONS.length}
Percentage: ${percentage}%
Result: ${result}
Thank you for taking the exam!
`;
    // Export as TXT
    const blob = new Blob([txt], { type: "text/plain" });
    const link = document.createElement("a");
    link.download = `${name}_exam_result.txt`;
    link.href = URL.createObjectURL(blob);
    link.click();

    // Export as PDF
    const doc = new jsPDF();
    doc.text("Exam Results", 10, 10);
    doc.text(`Name: ${name}`, 10, 20);
    doc.text(`Score: ${correct} / ${QUESTIONS.length}`, 10, 30);
    doc.text(`Percentage: ${percentage}%`, 10, 40);
    doc.text(`Result: ${result}`, 10, 50);
    doc.save(`${name}_exam_result.pdf`);
  };

  if (!started && !submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-purpleMain">
        <div className="bg-white rounded-2xl shadow-2xl p-12 w-full max-w-md">
          <h1 className="text-3xl font-bold text-purpleMain mb-6">Online Exam</h1>
          <input
            className="border-2 border-purpleMain rounded-lg px-4 py-2 w-full mb-4 focus:outline-none focus:border-purple-500"
            placeholder="Enter your name"
            value={name}
            onChange={e => setName(e.target.value)}
          />
          <button
            className="bg-purpleMain text-white font-semibold px-8 py-3 rounded-xl w-full hover:bg-purple-700 transition"
            disabled={!name}
            onClick={() => { setStarted(true); setTimeLeft(EXAM_TIME_SECONDS); }}
          >
            Start Exam
          </button>
        </div>
      </div>
    );
  }

  if (started && !submitted) {
    return (
      <div className="min-h-screen bg-purpleLight flex flex-col items-center py-10">
        <div className="w-full max-w-2xl bg-white shadow-xl rounded-2xl p-8">
          <div className="flex justify-between items-center mb-6">
            <div className="text-xl font-bold text-purpleMain">Welcome, {name}</div>
            <div className="font-mono text-lg text-purpleMain">
              Time Left: {Math.floor(timeLeft / 60)}:{String(timeLeft % 60).padStart(2, "0")}
            </div>
          </div>
          <form onSubmit={e => { e.preventDefault(); handleSubmit(); }}>
            {QUESTIONS.map((q, i) => (
              <div key={i} className="mb-6">
                <div className="font-semibold mb-2">{i + 1}. {q.question}</div>
                <div className="flex flex-col gap-2">
                  {q.options.map((opt, j) => (
                    <label key={j} className="flex items-center">
                      <input
                        type="radio"
                        name={`q${i}`}
                        checked={answers[i] === j}
                        onChange={() => handleOptionChange(i, j)}
                        className="accent-purpleMain mr-2"
                        required
                      />
                      <span>{opt}</span>
                    </label>
                  ))}
                </div>
              </div>
            ))}
            <button
              type="submit"
              className="bg-purpleMain text-white px-8 py-2 rounded-xl font-bold w-full hover:bg-purple-800 transition"
            >
              Submit
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Show results
  const percentage = ((score / QUESTIONS.length) * 100).toFixed(2);
  const passed = percentage >= PASS_MARK;

  return (
    <div className="min-h-screen flex items-center justify-center bg-purpleMain">
      <div className="bg-white rounded-2xl shadow-2xl p-12 w-full max-w-md text-center">
        <h2 className={`text-4xl font-bold mb-6 ${passed ? "text-green-600" : "text-red-600"}`}>
          {passed ? "Congratulations!" : "Exam Completed"}
        </h2>
        <div className="text-xl mb-4">Name: <span className="font-semibold">{name}</span></div>
        <div className="text-lg mb-2">Score: {score} / {QUESTIONS.length}</div>
        <div className="text-lg mb-2">Percentage: {percentage}%</div>
        <div className={`text-lg mb-8 font-bold ${passed ? "text-green-600" : "text-red-600"}`}>
          {passed ? "PASS" : "FAIL"}
        </div>
        <div className="text-purpleMain font-semibold mb-2">
          Results have been automatically downloaded (TXT & PDF)
        </div>
        <button
          className="mt-6 bg-purpleMain text-white px-6 py-2 rounded-xl font-bold"
          onClick={() => { setName(""); setAnswers(Array(QUESTIONS.length).fill(null)); setSubmitted(false); setScore(0); }}
        >
          Try Again
        </button>
      </div>
    </div>
  );
}

export default App;
