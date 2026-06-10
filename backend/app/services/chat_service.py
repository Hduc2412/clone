
#điều phối toàn bộ luồng xử lý từ câu hỏi đến câu trả lời
from app.rag.retriever import search
from app.rag.prompt_builder import build_context, build_prompt
from app.llm.gemini import generate_response

def process_message(user_query: str) -> dict:
    """
    Luồng chính:
    1. Tìm kiếm thông tin liên quan trong Qdrant
    2. Gộp thông tin thành context
    3. Xây dựng prompt hoàn chỉnh
    4. Gọi Gemini để tạo câu trả lời
    5. Trả về answer + sources
    """
    #1 tìm context liên quan
    hits = search(user_query)
    if not hits:
        return {
           "answer": "Xin lỗi, tôi không tìm thấy thông tin liên quan. Vui lòng liên hệ 0971.716.939 để được tư vấn trực tiếp.",
            "sources": []
        }
    #2 gộp context
    context = build_context(hits)
    prompt = build_prompt(context, user_query)

    #3 gọi gemini
    answer = generate_response(prompt)

    #4 tổng hợp sources
    sources = []
    seen = set()
    for hit in hits:
        url = hit.payload.get("url", "")
        if url and url not in seen:
            seen.add(url)
            sources.append({
                "title": hit.payload.get("title", ""),
                "url": url,
                "image": hit.payload.get("image", ""),
                "score": round(hit.score, 3)
            })

    return {"answer": answer, "sources": sources}
        

