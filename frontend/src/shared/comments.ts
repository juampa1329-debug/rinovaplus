export const commentPlatforms = ["Facebook", "Instagram", "TikTok"] as const;
export type SocialComment = {
  id: string;
  platform: (typeof commentPlatforms)[number];
  author: string;
  post: string;
  body: string;
  status: "Pendiente" | "Respondido";
  replies: { id: string; body: string }[];
};
export function seedComments(): SocialComment[] {
  return [];
}

export function filterComments(
  comments: SocialComment[],
  query: string,
  platform: string,
  status: string,
): SocialComment[] {
  return comments.filter(
    (comment) =>
      (platform === "Todas" || platform === comment.platform) &&
      (status === "Todos" || status === comment.status) &&
      [comment.author, comment.post, comment.body]
        .join(" ")
        .toLocaleLowerCase("es")
        .includes(query.trim().toLocaleLowerCase("es")),
  );
}
export function appendLocalReply(
  comment: SocialComment,
  body: string,
): SocialComment {
  if (!body.trim() || body.trim().length > 1500) return comment;
  return {
    ...comment,
    status: "Respondido",
    replies: [
      ...comment.replies,
      { id: crypto.randomUUID(), body: body.trim() },
    ],
  };
}
