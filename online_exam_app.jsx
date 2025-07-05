import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
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
  const percentElapsed = ((EXAM_DURATION - timeLeft) / EXAM_DURATION) * 100;

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

  // Generate and download PDF, also store metadata in localStorage
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
          className="w-full max-w-md"
        >
          <Card>
            <CardHeader className="text-center">
              <h1 className="text-2xl font-bold text-indigo-900">Welcome to the Purple Team Exam</h1>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input label="Student Name" placeholder="Enter your name" value={studentName} onChange={e => setStudentName(e.target.value)} />
              <Input label="Student ID" placeholder="Enter your ID" value={studentID} onChange={e => setStudentID(e.target.value)} />
              <Button onClick={handleStart} disabled={!studentName.trim() || !studentID.trim()} className="w-full mt-2">
                Start Exam
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  // Results screen
  if (showResults) {
    const percent = (score / questions.length) * 100;
    const passed = percent >= PASS_MARK * 100;
    return (
      <div className="min-h-screen bg-purple-50 flex items-center justify-center p-4">
        <motion.div initial={{ scale: 0.8, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ duration: 0.4 }} className="w-full max-w-md">
          <Card>
            <CardHeader className="text-center">
              <h2 className="text-2xl font-bold">Exam Results</h2>
            </CardHeader>
            <CardContent className="text-center space-y-4">
              <p>Name: <strong>{studentName}</strong></p>
              <p>ID: <strong>{studentID}</strong></p>
              {passed ? <CheckCircle className="mx-auto w-12 h-12 text-green-500"/> : <XCircle className="mx-auto w-12 h-12 text-red-500"/>}
              <p>Your Score: {percent.toFixed(2)}%</p>
              <p>Required: {(PASS_MARK*100).toFixed(0)}%</p>
              <Button onClick={exportResults} className="mt-4 inline-flex items-center">
                <Download className="mr-2"/> Export PDF & Save
              </Button>
            </CardContent>
          </Card>
        </motion.div>
      </div>
    );
  }

  // Exam screen
  return (
    <div className="min-h-screen bg-purple-50 flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }} className="w-full max-w-xl">
        <Card className="mb-6">
          <CardHeader className="flex justify-between items-center">
            <div>
              <h1 className="text-2xl font-bold text-indigo-900">Purple Team Exam</h1>
              <p className="text-sm text-indigo-700">Candidate: {studentName} (ID: {studentID})</p>
            </div>
            <div className="flex items-center space-x-2">
              <Clock className="w-5 h-5 text-indigo-600" />
              <span className="font-mono">{formatTime(timeLeft)}</span>
            </div>
          </CardHeader>
          <CardContent>
            <Progress value={percentElapsed} className="mb-4" />
            <h2 className="text-lg font-medium text-indigo-800 mb-2">Question {currentIndex+1} of {questions.length}</h2>
            <p className="mb-4 text-indigo-700">{currentQuestion.question}</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
              {currentQuestion.options.map(opt => (
                <Button key={opt} variant={selected===opt?'default':'outline'} onClick={()=>handleSelect(opt)} className="text-left">
                  {opt}
                </Button>
              ))}
            </div>
            <div className="text-right">
              <Button onClick={handleNext} disabled={!selected} className="px-6">
                {currentIndex+1===questions.length?'Submit':'Next'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
