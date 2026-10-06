import { Box, Card, Chip, Divider, Typography } from "@mui/material";
const SOURCE_LABELS = {
  ai_model: "AI model",
  rule_based: "Rule-based engine",
};
const formatConfidence = (confidence) => {
  if (typeof confidence !== "number" || Number.isNaN(confidence)) return null;
  return `${Math.round(Math.min(1, Math.max(0, confidence)) * 100)}%`;
};
const InsightList = ({ title, items, color }) => {
  if (!items.length) return null;
  return (
    <Box sx={{ mb: 2 }}>
      <Typography
        variant="overline"
        sx={{ fontWeight: 700, letterSpacing: 1.2, color: `${color}.main` }}
      >
        {title}
      </Typography>
      {items.map((item) => (
        <Box key={item.factor} sx={{ mt: 0.75 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {item.factor}
          </Typography>
          {item.description && (
            <Typography variant="caption" color="text.secondary">
              {item.description}
            </Typography>
          )}
        </Box>
      ))}
    </Box>
  );
};
const ScoreInsights = ({ creditData }) => {
  const source = creditData?.scoring_source;
  const sourceLabel = SOURCE_LABELS[source];
  const confidence = formatConfidence(creditData?.confidence);
  const positive = creditData?.insights?.positive || [];
  const negative = creditData?.insights?.negative || [];
  if (!creditData || (!sourceLabel && !confidence)) {
    return null;
  }
  return (
    <Card sx={{ height: "100%", p: 3 }}>
      <Typography sx={{ fontWeight: 600, mb: 1.5 }}>
        How this score was calculated
      </Typography>

      <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", mb: 2 }}>
        {sourceLabel && (
          <Chip
            size="small"
            label={sourceLabel}
            color={source === "ai_model" ? "primary" : "default"}
          />
        )}
        {confidence && (
          <Chip
            size="small"
            variant="outlined"
            label={`Confidence ${confidence}`}
          />
        )}
        {creditData.model_name && source === "ai_model" && (
          <Chip
            size="small"
            variant="outlined"
            label={`${creditData.model_name} v${
              creditData.model_version || "?"
            }`}
          />
        )}
      </Box>

      {source === "rule_based" && (
        <Typography variant="body2" color="text.secondary">
          The AI scoring service was unavailable or had no usable history, so
          this score comes from the built-in multi-factor rules.
        </Typography>
      )}

      {(positive.length > 0 || negative.length > 0) && (
        <>
          <Divider sx={{ mb: 2 }} />
          <InsightList
            title="Helping your score"
            items={positive}
            color="success"
          />
          <InsightList
            title="Hurting your score"
            items={negative}
            color="error"
          />
        </>
      )}
    </Card>
  );
};
export default ScoreInsights;
