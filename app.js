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
const EXAM_TIME_SECONDS = 60 * 5; // 5 minutes for demo

export default function App() {
  const [name, setName] = useState("");
  const [started, setStarted] = useState(false);
  const [currentQ, setCurrentQ] = useState(0);
  const [answers, setAnswers] = useState(Array(QUESTIONS.length).fill(null));
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState(0);
  const [timeLeft, setTimeLeft] = useState(EXAM_TIME_SECONDS);

  // Timer logic
  useEffect(() => {
    if (!started || submitted) return;
    if (timeLeft <= 0) {
      handleSubmit();
      return;
    }
    const timer = setInterval(() => setTimeLeft(t => t - 1), 1000);
    return () => clearInterval(timer);
  }, [started, timeLeft, submitted]);

  const handleOptionChange = (idx) => {
    const updated = [...answers];
    updated[currentQ] = idx;
    setAnswers(updated);
  };

  const handleNext = () => {
    if (currentQ < QUESTIONS.length - 1) {
      setCurrentQ(currentQ + 1);
    } else {
      handleSubmit();
    }
  };

  const handlePrev = () => {
    if (currentQ > 0) setCurrentQ(currentQ - 1);
  };

  const handleSubmit = () => {
    let correctCount = 0;
    answers.forEach((ans, idx) => {
      if (ans === QUESTIONS[idx].answer) correctCount++;
    });
    setScore(correctCount);
    setSubmitted(true);
    setStarted(false);
    setTimeLeft(0);
    setTimeout(() => exportResults(correctCount), 500);
  };

  const exportResults = (correctCount) => {
    const percent = ((correctCount / QUESTIONS.length) * 100).toFixed(2);
    const result = percent >= PASS_MARK ? "PASS" : "FAIL";
    const textContent = `Name: ${name}\nScore: ${correctCount} / ${QUESTIONS.length}\nPercentage: ${percent}%\nResult: ${result}`;
    // TXT download
    const blob = new Blob([textContent], { type: 'text/plain' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${name}_result.txt`;
    link.click();

    // PDF download
    const doc = new jsPDF();
    doc.setFontSize(16);
    doc.setTextColor(76, 0, 153);
    doc.text('Exam Results', 20, 20);
    doc.setFontSize(12);
    doc.text(`Name: ${name}`, 20, 40);
    doc.text(`Score: ${correctCount} / ${QUESTIONS.length}`, 20, 50);
    doc.text(`Percentage: ${percent}%`, 20, 60);
    doc.text(`Result: ${result}`, 20, 70);
    doc.save(`${name}_result.pdf`);
  };

  // Initial Name Entry
  if (!started && !submitted) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-900 to-purple-800">
        <div className="bg-white p-8 rounded-3xl shadow-2xl max-w-sm w-full">
          <h1 className="text-3xl font-extrabold mb-6 text-center text-purple-900">Start Exam</h1>
          <input
            type="text"
            placeholder="Your Name"
            value={name}
            onChange={e => setName(e.target.value)}
            className="w-full border-2 border-purple-900 rounded-lg px-4 py-2 mb-4 focus:outline-none focus:ring-2 focus:ring-purple-900 placeholder-purple-900 text-purple-900 bg-white"
          />
          <button
            disabled={!name}
            onClick={() => { setStarted(true); setTimeLeft(EXAM_TIME_SECONDS); }}
            className="w-full bg-purple-900 hover:bg-purple-950 text-white font-semibold py-3 rounded-lg focus:outline-none focus:ring-4 focus:ring-purple-700 disabled:opacity-50 transition"
          >Begin</button>
        </div>
      </div>
    );
  }

  // Question Pages
  if (started && !submitted) {
    const q = QUESTIONS[currentQ];
    const progress = ((currentQ + 1) / QUESTIONS.length) * 100;
    return (
      <div className="min-h-screen bg-purple-900 flex flex-col items-center py-8">
        <div className="w-full max-w-xl bg-purple-800 rounded-3xl shadow-2xl p-6">
          <div className="flex justify-between items-center mb-4">
            <span className="text-xl font-bold text-white">{name}</span>
            <span className="font-mono text-lg text-white">
              {Math.floor(timeLeft/60)}:{String(timeLeft%60).padStart(2,'0')}
            </span>
          </div>
          {/* Progress Bar */}
          <div className="w-full bg-purple-500 rounded-full h-3 mb-6">
            <div
              className="bg-purple-200 h-3 rounded-full transition-all"
              style={{ width: `${progress}%` }}
            />
          </div>
          <div className="border-2 border-purple-200 rounded-2xl p-6 mb-6 bg-purple-200">
            <div className="text-lg font-semibold text-purple-900 mb-4">Question {currentQ+1} of {QUESTIONS.length}</div>
            <div className="mb-4 text-base text-purple-900">{q.question}</div>
            <div className="flex flex-col space-y-3">
              {q.options.map((opt, idx) => (
                <label
                  key={idx}
                  className={`flex items-center p-3 border-2 rounded-lg cursor-pointer transition ${answers[currentQ] === idx ? 'border-green-500 bg-green-500' : 'border-transparent'} focus-within:ring-2 focus-within:ring-green-400`}
                >
                  <input
                    type="radio"
                    name={`q${currentQ}`}
                    checked={answers[currentQ] === idx}
                    onChange={() => handleOptionChange(idx)}
                    className="accent-green-500 focus:ring-green-400 mr-3"
                  />
                  <span className="text-purple-900">{opt}</span>
                </label>
              ))}
            </div>
          </div>
          <div className="flex justify-between">
            <button
              onClick={handlePrev}
              disabled={currentQ === 0}
              className="px-4 py-2 bg-white text-purple-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-700 disabled:opacity-50 transition"
            >Previous</button>
            <button
              onClick={handleNext}
              disabled={answers[currentQ] === null}
              className="px-4 py-2 bg-white text-purple-900 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-700 disabled:opacity-50 transition"
            >{currentQ < QUESTIONS.length - 1 ? 'Next' : 'Submit'}</button>
          </div>
        </div>
      </div>
    );
  }

  // Results Screen
  const percentScore = ((score / QUESTIONS.length) * 100).toFixed(2);
  const pass = percentScore >= PASS_MARK;
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-purple-900 to-purple-800 text-white">
      <div className="bg-purple-200 p-8 rounded-3xl shadow-2xl max-w-sm w-full text-center">
        <h2 className={`text-3xl font-bold mb-4 ${pass ? 'text-green-200' : 'text-red-200'}`}>{pass ? 'Passed!' : 'Completed'}</h2>
        <p className="mb-2 text-lg text-purple-900">Name: <span className="font-semibold text-purple-900">{name}</span></p>
        <p className="mb-2 text-lg text-purple-900">Score: {score} / {QUESTIONS.length}</p>
        <p className="mb-4 text-lg text-purple-900">Percentage: {percentScore}%</p>
        <p className="mb-6 font-semibold text-purple-900">Results downloaded (TXT & PDF)</p>
        <button
          onClick={() => window.location.reload()}
          className="px-6 py-2 bg-white text-purple-900 rounded-lg focus:outline-none focus:ring-4 focus:ring-purple-700 transition"
        >Retake Exam</button>
      </div>
    </div>
  );
}
