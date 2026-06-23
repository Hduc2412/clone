import ChatWidget from "@/components/ChatWidget";

export default function Home() {
  return (
    <main className="min-h-screen bg-white">
      {/* Nội dung website bình thường ở đây */}
      <div className="flex items-center justify-center h-screen text-gray-400 text-sm">
        Website xklddieuduong.vn
      </div>

      {/* Widget chat cố định góc phải */}
      <ChatWidget />
    </main>
  );
}