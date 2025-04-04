"use client"

import { Document, Page, Text, View, StyleSheet, PDFDownloadLink, pdf } from '@react-pdf/renderer';

// PDF styles
const styles = StyleSheet.create({
  page: {
    flexDirection: 'column',
    backgroundColor: '#fff',
    padding: 30,
  },
  section: {
    margin: 10,
    padding: 10,
  },
  title: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 10,
    color: '#555',
  },
  metadata: {
    marginBottom: 20,
    borderBottom: '1pt solid #ddd',
    paddingBottom: 10,
  },
  metaRow: {
    flexDirection: 'row',
    marginBottom: 8,
  },
  metaLabel: {
    width: '30%',
    fontSize: 10,
    color: '#555',
  },
  metaValue: {
    width: '70%',
    fontSize: 10,
    fontWeight: 'bold',
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    marginBottom: 10,
    marginTop: 15,
    backgroundColor: '#f5f5f5',
    padding: '5 10',
    color: '#333',
  },
  text: {
    fontSize: 10,
    marginBottom: 10,
    lineHeight: 1.5,
    textAlign: 'justify',
  },
  score: {
    fontSize: 12,
    fontWeight: 'bold',
    textAlign: 'center',
    marginVertical: 10,
    padding: 5,
    backgroundColor: '#f0f0f0',
  },
  recommendation: {
    fontSize: 10,
    fontWeight: 'bold',
    marginVertical: 10,
    padding: 5,
  },
  recommendationAccepted: {
    color: '#2e7d32',
    backgroundColor: '#e8f5e9',
  },
  recommendationRevision: {
    color: '#ef6c00',
    backgroundColor: '#fff3e0',
  },
  recommendationRejected: {
    color: '#c62828',
    backgroundColor: '#ffebee',
  },
  footer: {
    position: 'absolute',
    bottom: 30,
    left: 30,
    right: 30,
    fontSize: 8,
    textAlign: 'center',
    color: '#999',
    borderTop: '1pt solid #ddd',
    paddingTop: 10,
  },
});

// ReviewDocument type
interface ReviewDocumentProps {
  trackingNumber: string;
  paperTitle: string;
  reviewDate: string;
  score: number;
  recommendation: string;
  comments: string;
}

// Review PDF document
const ReviewDocument = ({ 
  trackingNumber, 
  paperTitle, 
  reviewDate, 
  score, 
  recommendation, 
  comments
}: ReviewDocumentProps) => {
  // Determine recommendation style
  const getRecommendationStyle = () => {
    switch(recommendation) {
      case 'accepted':
        return {...styles.recommendation, ...styles.recommendationAccepted};
      case 'revision_required':
        return {...styles.recommendation, ...styles.recommendationRevision};
      case 'rejected':
        return {...styles.recommendation, ...styles.recommendationRejected};
      default:
        return styles.recommendation;
    }
  };

  // Determine recommendation text
  const getRecommendationText = () => {
    switch(recommendation) {
      case 'accepted':
        return 'ACCEPT: Article should be accepted directly';
      case 'revision_required':
        return 'REVISION: Corrections required';
      case 'rejected':
        return 'REJECT: Article should be rejected';
      default:
        return recommendation;
    }
  };

  return (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>Article Review Report</Text>
        
        {/* Metadata section */}
        <View style={styles.metadata}>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Tracking No:</Text>
            <Text style={styles.metaValue}>{trackingNumber}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Article Title:</Text>
            <Text style={styles.metaValue}>{paperTitle}</Text>
          </View>
          <View style={styles.metaRow}>
            <Text style={styles.metaLabel}>Review Date:</Text>
            <Text style={styles.metaValue}>{reviewDate}</Text>
          </View>
        </View>
        
        {/* Review Summary */}
        <Text style={styles.sectionTitle}>REVIEW SUMMARY</Text>
        
        {/* Score */}
        <Text style={styles.score}>
          Review Score: {score}/10
        </Text>
        
        {/* Recommendation */}
        <Text style={getRecommendationStyle()}>
          {getRecommendationText()}
        </Text>
        
        {/* Comments */}
        <Text style={styles.sectionTitle}>REVIEW</Text>
        <Text style={styles.text}>
          {comments}
        </Text>
        
        {/* Footer */}
        <Text style={styles.footer}>
          This review report was created on {reviewDate}.
          This document is prepared as part of the article review process and is confidential.
        </Text>
      </Page>
    </Document>
  );
};

// ReviewPdfGenerator component props type
interface ReviewPdfGeneratorProps {
  trackingNumber: string;
  paperTitle: string;
  fileName?: string;
  score: number;
  recommendation: string;
  comments: string;
}

// ReviewPdfGenerator type için generatePdf fonksiyonu
export const generatePdf = async ({
  trackingNumber,
  paperTitle,
  score,
  recommendation,
  comments
}: ReviewPdfGeneratorProps): Promise<{ blob: Blob }> => {
  // Format today's date - English
  const reviewDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  
  // PDF dokümanını oluştur
  const pdfDocument = (
    <ReviewDocument
      trackingNumber={trackingNumber}
      paperTitle={paperTitle}
      reviewDate={reviewDate}
      score={score}
      recommendation={recommendation}
      comments={comments}
    />
  );
  
  // Dokümanı PDF'e dönüştür
  const blob = await pdf(pdfDocument).toBlob();
  return { blob };
};

// ReviewPdfGenerator component - creates PDF download link
const ReviewPdfGenerator = ({
  trackingNumber,
  paperTitle,
  fileName,
  score,
  recommendation,
  comments
}: ReviewPdfGeneratorProps) => {
  // Format today's date - English
  const reviewDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });
  
  // Download file name
  const downloadFileName = fileName || `review-${trackingNumber}.pdf`;
  
  return (
    <PDFDownloadLink
      document={
        <ReviewDocument
          trackingNumber={trackingNumber}
          paperTitle={paperTitle}
          reviewDate={reviewDate}
          score={score}
          recommendation={recommendation}
          comments={comments}
        />
      }
      fileName={downloadFileName}
      className="inline-block"
    >
      {({ loading }) => 
        loading ? 'Preparing PDF...' : 'Download as PDF'
      }
    </PDFDownloadLink>
  );
};

export default ReviewPdfGenerator; 