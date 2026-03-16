import React, { useState } from 'react';

interface Props {
  messageId: string;
}

export default function FeedbackButtons({ messageId }: Props) {
  const [submitted, setSubmitted] = useState<boolean>(false);

  async function sendFeedback(rating: 'up' | 'down') {
    try {
      await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/feedback/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message_id: messageId, rating }),
      });
      setSubmitted(true);
    } catch (err) {
      console.error(err);
    }
  }

  if (submitted) return <p className="text-sm mt-2">Thank you for your feedback!</p>;

  return (
    <div className="flex space-x-2 mt-2">
      <button
        className="px-2 py-1 text-sm bg-green-200 rounded"
        onClick={() => sendFeedback('up')}
      >
        👍 Helpful
      </button>
      <button
        className="px-2 py-1 text-sm bg-red-200 rounded"
        onClick={() => sendFeedback('down')}
      >
        👎 Unhelpful
      </button>
    </div>
  );
}