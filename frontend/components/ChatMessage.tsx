import Image from "next/image";
import ReactMarkdown from "react-markdown";
import { Message } from "@/lib/api";

interface ChatMessageProps {
  message: Message;
  compact?: boolean;
}

export default function ChatMessage({
  message,
  compact = false,
}: ChatMessageProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`${compact ? "max-w-[80%] px-3 py-2" : "max-w-[75%] px-4 py-2.5"} rounded-2xl text-sm leading-relaxed ${
          isUser
            ? "text-white"
            : "bg-white text-gray-800 border border-gray-200 shadow-sm"
        }`}
        style={isUser ? { backgroundColor: "#cb1d1e" } : {}}
      >
        <ReactMarkdown>{message.content}</ReactMarkdown>

        {message.image && (
          <div className="mt-2">
            <p className="text-xs text-gray-400 mb-1">
              Anh/chị có thể tham khảo ảnh bên dưới:
            </p>
            <div className="relative w-full aspect-[4/3]">
              <Image
                src={message.image}
                alt="Ảnh minh họa từ bài viết"
                fill
                sizes={compact ? "280px" : "(max-width: 768px) 75vw, 560px"}
                className="rounded-lg object-contain"
              />
            </div>
          </div>
        )}

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 border-t border-gray-100 pt-2">
            <p className="text-xs font-medium text-gray-500 mb-1">
              Nguồn trả lời
            </p>
            <ul className="space-y-1">
              {message.sources.map((source) => (
                <li key={source.url}>
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs text-blue-600 hover:underline"
                  >
                    {source.is_primary && (
                      <span className="font-medium">Nguồn chính: </span>
                    )}
                    {source.title || source.url}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
