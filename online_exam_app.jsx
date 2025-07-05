import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Clock, CheckCircle, XCircle, Download } from 'lucide-react';
import jsPDF from 'jspdf';

// Question pool for Purple Team MCQ exam
const questions = [
  {
    id: 1,
    question: 'What is the primary goal of Purple Team exercises?',
    options: [
      'A) Improve Red Team tactics',
      'B) Improve Blue Team defenses',
      'C) Foster collaboration between Red and Blue Teams',
      'D) Practice physical security protocols'
    ],
    answer: 'C'
  },
  {
    id: 2,
    question: 'Which phase involves simulating attacker techniques?',
    options: [
      'A) Blue Team Analysis',
      'B) Red Team Engagement',
      'C) Purple Team Review',
      'D) Post-Incident Response'
    ],
    answer: 'B'
  },
  // ... additional questions ...
];

const PASS_MARK = 0.75;
const EXAM_DURATION = 10 * 60; // seconds

export default function App() {
  const [studentName, setStudentName] = useState('');
  const [studentID, setStudentID] = useState('');
  const [started, setStarted] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [selected, setSelected] = useState('');
  const [score, setScore] = useState(0);
  const [showResults, setShowResults] = useState(false);
  const [timeLeft, setTimeLeft] = useState(EXAM_DURATION);

  // Timer effect
  useEffect(() => {
    if (!started || showResults) return;
    if (timeLeft <= 0) {
      setShowResults(true);
      return;
    }
    const id = setInterval(() => setTimeLeft(t => t - 1), 1000);
    return () => clearInterval(id);
  }, [started, timeLeft, showResults]);

  const handleStart = () => {
    if (!studentName.trim() || !studentID.trim()) return;
    setStarted(true);
  };

  // Safe question access
  const currentQuestion = questions[currentIndex] || { question: '', options: [], answer: '' };
  const percentElapsed = Math.min(100, ((EXAM_DURATION - timeLeft) / EXAM_DURATION) * 100);

  const handleSelect = option => setSelected(option);

  const handleNext = () => {
    if (currentQuestion.answer && selected.charAt(0) === currentQuestion.answer) {
      setScore(prev => prev + 1);
    }
    setSelected('');
    if (currentIndex + 1 < questions.length) setCurrentIndex(prev => prev + 1);
    else setShowResults(true);
  };

  const formatTime = secs =>
    `${String(Math.floor(secs / 60)).padStart(2, '0')}:${String(secs % 60).padStart(2, '0')}`;

  const exportResults = () => {
    const percent = ((score / questions.length) * 100).toFixed(2);
    const passed = percent >= PASS_MARK * 100;
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.text('Purple Team Exam Results', 20, 20);
    doc.setFontSize(12);
    doc.text(`Name: ${studentName}`, 20, 40);
    doc.text(`ID: ${studentID}`, 20, 50);
    doc.text(`Score: ${percent}%`, 20, 60);
    doc.text(`Result: ${passed ? 'Passed' : 'Failed'}`, 20, 70);
    const filename = `${studentName}_${studentID}_results.pdf`;
    doc.save(filename);

    // Store record
    const records = JSON.parse(localStorage.getItem('examRecords') || '[]');
    records.push({ name: studentName, id: studentID, score: Number(percent), passed, date: new Date().toISOString() });
    localStorage.setItem('examRecords', JSON.stringify(records));
  };

  // Start screen
  if (!started) {
    return (
      <div className="min-h-screen bg-purple-50 flex items-center justify-center p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.4 }}
          className="w-full max-w-md bg-white rounded-2xl shadow-lg p-6"
        >
          <h1 className="text-2xl font-bold text-indigo-900 text-center mb-4">Welcome to the Purple Team Exam</h1>
          <label className="block text-sm font-medium text-indigo-800 mb-1">Student Name</label>
          <input
            type="text"
            placeholder="Enter your name"
            value={studentName}
            onChange={e => setStudentName(e.target.value)}
            className="w-full px-4 py-2 mb-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <label className="block text-sm font-medium text-indigo-800 mb-1">Student ID</label>
          <input
            type="text"
            placeholder="Enter your ID"
            value={studentID}
            onChange={e => setStudentID(e.target.value)}
            className="w-full px-4 py-2 mb-4 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-indigo-400"
          />
          <button
            onClick={handleStart}
            disabled={!studentName.trim() || !studentID.trim()}
            className="w-full py-2 mt-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            Start Exam
          </button>
        </motion.div>
      </div>
    );
  }

  // Results screen
  if (showResults) {
    const percent = ((score / questions.length) * 100).toFixed(2);
    const passed = percent >= PASS_MARK * 100;
    return (
      <div className="min-h-screen bg-purple-50 flex items-center justify-center p-4">
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.4 }} className="w-full max-w-md bg-white rounded-2xl shadow-lg p-6">
          <div className="text-center">
            <h2 className="text-2xl font-bold mb-4">Exam Results</h2>
            <p className="text-indigo-700">Name: <strong>{studentName}</strong></p>
            <p className="text-indigo-700 mb-4">ID: <strong>{studentID}</strong></p>
            {passed ? <CheckCircle className="mx-auto w-12 h-12 text-green-500 mb-4"/> : <XCircle className="mx-auto w-12 h-12 text-red-500 mb-4"/>}
            <p className="text-lg mb-2">Your Score: <span className="font-mono">{percent}%</span></p>
            <p className="text-sm text-gray-600 mb-6">Required: {(PASS_MARK*100).toFixed(0)}%</p>
            <button
              onClick={exportResults}
              className="inline-flex items-center px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              <Download className="mr-2"/> Export PDF & Save
            </button>
          </div>
        </motion.div>
      </div>
    );
  }

  // Exam screen
  return (
    <div className="min-h-screen bg-purple-50 flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="w-full max-w-xl bg-white rounded-2xl shadow-lg p-6">
        <div className="flex justify-between items-center mb-4">
          <div>
            <h1 className="text-2xl font-bold text-indigo-900">Purple Team Exam</h1>
            <p className="text-sm text-indigo-700">Candidate: {studentName} (ID: {studentID})</p>
          </div>
          <div className="flex items-center space-x-2">
            <Clock className="w-5 h-5 text-indigo-600" />
            <span className="font-mono">{formatTime(timeLeft)}</span>
          </div>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
          <div className="bg-indigo-600 h-2 rounded-full" style={{ width: `${percentElapsed}%` }} />
        </div>
        <h2 className="text-lg font-medium text-indigo-800 mb-2">Question {currentIndex + 1} of {questions.length}</h2>
        <p className="mb-4 text-indigo-700">{currentQuestion.question}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
          {currentQuestion.options.map(opt => (
            <button
              key={opt}
              onClick={() => handleSelect(opt)}
              className={`text-left px-4 py-2 border rounded hover:bg-indigo-50 disabled:opacity-50 ${selected === opt ? 'border-indigo-600 bg-indigo-100' : 'border-gray-300'}`}
            >
              {opt}
            </button>
          ))}
        </div>
        <div className="text-right">
          <button
            onClick={handleNext}
            disabled={!selected}
            className="px-6 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700 disabled:opacity-50"
          >
            {currentIndex + 1 === questions.length ? 'Submit' : 'Next'}
          </button>
        </div>
      </motion.div>
    </div>
  );
}
