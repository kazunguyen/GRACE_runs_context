import math

def binary_metrics(labels, predictions):
    if len(labels) != len(predictions) or not labels: raise ValueError('Labels/predictions must have equal non-zero length')
    if any(y not in (0, 1) for y in labels): raise ValueError('Labels must be binary')
    valid = [(int(y), int(p)) for y,p in zip(labels,predictions) if p in (0,1)]
    invalid_n = len(labels)-len(valid)
    tp=sum(y==1 and p==1 for y,p in valid); tn=sum(y==0 and p==0 for y,p in valid)
    fp=sum(y==0 and p==1 for y,p in valid); fn=sum(y==1 and p==0 for y,p in valid)
    div=lambda n,d:n/d if d else 0.0
    precision=div(tp,tp+fp); recall=div(tp,tp+fn)
    denom=math.sqrt((tp+fp)*(tp+fn)*(tn+fp)*(tn+fn))
    return {'n':len(labels),'valid_n':len(valid),'invalid_n':invalid_n,'invalid_rate':invalid_n/len(labels),
      'confusion_matrix_valid_only':{'tp':tp,'tn':tn,'fp':fp,'fn':fn},'precision':precision,'recall':recall,
      'f1':div(2*precision*recall,precision+recall),'mcc':div(tp*tn-fp*fn,denom),
      'balanced_accuracy':(recall+div(tn,tn+fp))/2,'accuracy_valid_only':div(tp+tn,len(valid)),
      'accuracy_all':div(tp+tn,len(labels)),'recall_all_positives':div(tp,sum(y==1 for y in labels)),
      'predicted_positive_rate_all':sum(p==1 for p in predictions)/len(predictions),
      'invalid_positive_n':sum(y==1 and p is None for y,p in zip(labels,predictions)),
      'metric_scope':'Binary scores use valid predictions; invalid responses remain counted separately.'}
