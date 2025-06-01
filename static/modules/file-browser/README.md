# File Browser Module - Modern Knowledge Base Explorer

A sophisticated, Typesense-powered file browser that transforms document discovery into an intuitive, search-driven experience. Built with modern web technologies and designed for maximum usability.

## 🌟 Features

### 🔍 **Intelligent Search**
- **Full-text search** across titles, descriptions, and summaries
- **Semantic/vector search** using OpenAI embeddings via Typesense auto-embedding
- **Real-time search** with debounced input (300ms delay)
- **Search highlighting** of matching terms in results
- **Keyboard shortcuts** (Ctrl/Cmd + K to focus search, Escape to clear)

### 🎛️ **Advanced Filtering**
- **Faceted filtering** by document type, category, language, authors, and tags
- **Dynamic filter counts** showing available options based on current search
- **Active filter pills** with easy removal
- **Filter persistence** during search sessions
- **Smart filter combinations** using Typesense filter syntax

### 📊 **Multiple View Modes**
- **List view** - Detailed horizontal layout (default)
- **Grid view** - Card-based layout for visual browsing
- **Responsive design** - Adapts to all screen sizes
- **View preference persistence** using localStorage

### 🎨 **Modern UI/UX**
- **Glass-morphism design** with backdrop filters and subtle shadows
- **Smooth animations** with staggered document card appearances
- **Interactive micro-animations** on hover and focus states
- **Elegant color-coded document type icons**
- **Professional typography** with Inter font family

### 📱 **Mobile-First Design**
- **Responsive sidebar** that collapses to offcanvas on mobile
- **Touch-friendly interactions** with proper touch targets
- **Optimized performance** for mobile devices
- **Progressive enhancement** with fallbacks

### ⚡ **Performance Optimizations**
- **Debounced search** to prevent excessive API calls
- **Pagination** with customizable page sizes
- **Lazy loading** of filter options
- **Efficient DOM manipulation** with minimal reflows
- **Caching** of user preferences

## 🏗️ Architecture

### Frontend Structure
```
static/modules/file-browser/
├── file-browser.html          # Main HTML interface
├── css/
│   └── file-browser.css      # Modern styling with CSS variables
├── js/
│   └── file-browser.js       # Core JavaScript functionality
└── README.md                 # This documentation
```

### Backend Integration
- **API Endpoint**: `/api/v1/documents/search`
- **Search Engine**: Typesense with auto-embedding
- **Authentication**: Inherits from main application
- **Data Format**: JSON responses with standardized structure

## 🔌 API Integration

### Search Endpoint
```
GET /api/v1/documents/search
```

**Parameters:**
- `q` (required): Search query string
- `query_by`: Fields to search in (default: "title,description,summary")
- `filter_by`: Filter conditions (e.g., "type:=document && language:=en")
- `facet_by`: Facet fields (default: "type,category,language,authors,tags")
- `sort_by`: Sort order (default: "created_at:desc")
- `page`: Page number (1-based)
- `per_page`: Results per page (1-100)
- `include_facet_counts`: Include facet counts (boolean)
- `highlight_full_fields`: Fields to highlight
- `use_vector_search`: Enable semantic search (boolean)

**Response Format:**
```json
{
  "success": true,
  "query": "search terms",
  "found": 42,
  "out_of": 100,
  "page": 1,
  "per_page": 12,
  "total_pages": 4,
  "search_time_ms": 15,
  "documents": [...],
  "facet_counts": [...],
  "metadata": {...}
}
```

### Document Object Schema
```json
{
  "id": "doc_123",
  "title": "Document Title",
  "description": "Brief description...",
  "summary": "Longer summary...",
  "type": "document",
  "category": "general",
  "authors": ["Author Name"],
  "tags": ["tag1", "tag2"],
  "date": "2024-01-15",
  "language": "en",
  "word_count": 1500,
  "page_count": 5,
  "file_path": "/path/to/file",
  "original_filename": "document.pdf",
  "created_at": 1705334400,
  "updated_at": 1705334400,
  "score": 0.85,
  "highlights": [...],
  "text_match": 95
}
```

## 🎯 Usage

### Basic Search
1. **Enter search terms** in the prominent search bar
2. **View results** in real-time as you type
3. **Click documents** to open detailed preview modal
4. **Use filters** to narrow down results

### Advanced Filtering
1. **Choose document type** (Academic Paper, Report, Manual, etc.)
2. **Filter by category** based on content classification
3. **Select language** for multilingual document collections
4. **Filter by authors** to find documents by specific creators
5. **Use tags** for topic-based filtering

### Keyboard Shortcuts
- `Ctrl/Cmd + K` - Focus search input
- `Escape` - Clear current search
- `Enter` - Execute search (when in search input)

### View Modes
- **List View** - Horizontal layout showing more metadata
- **Grid View** - Card-based layout for visual browsing
- Toggle using the view buttons in the header toolbar

## 🎨 Styling & Theming

### CSS Variables
The module uses CSS custom properties for easy theming:

```css
:root {
  --primary-color: #3498db;
  --secondary-color: #2c3e50;
  --accent-color: #e74c3c;
  --border-radius: 12px;
  --shadow-md: 0 4px 8px rgba(0,0,0,0.12);
  --transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
```

### Document Type Colors
Each document type has a unique color scheme:
- **Document**: Blue gradient
- **Academic Paper**: Purple gradient
- **Report**: Red gradient
- **Manual**: Orange gradient
- **Presentation**: Green gradient
- **Policy**: Dark gray gradient

### Responsive Breakpoints
- **Mobile**: < 768px (sidebar collapses, single column grid)
- **Tablet**: 768px - 1024px (responsive grid)
- **Desktop**: > 1024px (full layout with sidebar)

## 🔧 Configuration

### JavaScript Configuration
```javascript
// File Browser instance configuration
const fileBrowser = new FileBrowser({
  apiEndpoint: window.location.origin,
  perPage: 12,                    // Results per page
  searchDelay: 300,               // Debounce delay in ms
  defaultSort: 'created_at:desc', // Default sort order
  defaultView: 'list'             // Default view mode
});
```

### LocalStorage Keys
The module stores user preferences in localStorage:
- `fileBrowser_viewMode` - Current view mode (list/grid)
- `fileBrowser_sortOrder` - Preferred sort order
- `fileBrowser_searchHistory` - Recent search terms

## 🚀 Performance Features

### Search Optimization
- **Debounced input** prevents excessive API calls
- **Request deduplication** avoids duplicate searches
- **Progressive loading** of filter options
- **Efficient DOM updates** using document fragments

### Memory Management
- **Event listener cleanup** prevents memory leaks
- **Lazy component initialization** reduces initial load time
- **Efficient data structures** for filter management

### Network Optimization
- **Compressed API responses** with gzip
- **Smart caching** of search results
- **Minimal payload** with only required fields

## 📱 Mobile Experience

### Touch Interactions
- **Swipe gestures** for navigation (future enhancement)
- **Touch-friendly** filter toggles
- **Optimized tap targets** (minimum 44px)

### Responsive Design
- **Collapsible sidebar** becomes mobile drawer
- **Stacked layout** on small screens
- **Readable typography** with appropriate scaling

### Performance on Mobile
- **Optimized images** and assets
- **Reduced animations** on low-power devices
- **Efficient touch handling** without delays

## 🔍 Search Capabilities

### Query Types
1. **Simple text search**: `machine learning`
2. **Phrase search**: `"artificial intelligence"`
3. **Wildcard search**: `AI*` or `*learning`
4. **Boolean search**: `AI AND machine learning`

### Filter Syntax
- **Exact match**: `type:=document`
- **Multiple values**: `type:[document,report]`
- **Boolean combinations**: `type:=document && language:=en`
- **Numeric ranges**: `word_count:>1000`

### Sorting Options
- **Newest First**: `created_at:desc`
- **Oldest First**: `created_at:asc`
- **Title A-Z**: `title:asc`
- **Title Z-A**: `title:desc`
- **Longest First**: `word_count:desc`
- **Shortest First**: `word_count:asc`
- **Relevance**: Based on search score

## 🎭 State Management

### Application States
1. **Empty State** - No search query or filters
2. **Loading State** - Search in progress
3. **Results State** - Displaying search results
4. **No Results State** - Search returned no documents
5. **Error State** - Search failed or API error

### State Transitions
```
Empty → Loading → Results
      ↘ Loading → No Results
      ↘ Loading → Error → Empty
```

## 🔐 Security Features

### Input Sanitization
- **XSS prevention** with proper HTML escaping
- **SQL injection protection** via parameterized queries
- **CSRF protection** inherited from main application

### API Security
- **Rate limiting** on search endpoints
- **Authentication** required for access
- **Input validation** on all parameters

## 🚦 Error Handling

### User-Friendly Messages
- **Connection errors**: "Unable to connect. Please check your internet."
- **Search errors**: "Search failed. Please try different terms."
- **Timeout errors**: "Search is taking longer than expected."

### Graceful Degradation
- **Fallback states** when API is unavailable
- **Progressive enhancement** for older browsers
- **Accessibility** maintained in error states

## 🔮 Future Enhancements

### Planned Features
- [ ] **Saved searches** and search history
- [ ] **Document collections** and favorites
- [ ] **Advanced search builder** with visual query construction
- [ ] **Export functionality** for search results
- [ ] **Real-time collaboration** features
- [ ] **AI-powered search suggestions**
- [ ] **Document preview** without modal
- [ ] **Bulk operations** on search results

### Technical Improvements
- [ ] **Service Worker** for offline functionality
- [ ] **Virtual scrolling** for large result sets
- [ ] **Search analytics** and usage tracking
- [ ] **A/B testing** framework integration
- [ ] **Performance monitoring** with Core Web Vitals

## 📊 Analytics & Monitoring

### Search Metrics
- **Search volume** and frequency
- **Popular search terms** and patterns
- **Filter usage** statistics
- **User session** analysis

### Performance Metrics
- **Search response times** from Typesense
- **Page load times** and Core Web Vitals
- **Error rates** and failure patterns
- **User engagement** metrics

## 🤝 Contributing

### Development Setup
1. Ensure the main Agentic RAG application is running
2. Typesense should be running with indexed documents
3. Modify files in `static/modules/file-browser/`
4. Test across different browsers and devices

### Code Style
- Follow existing JavaScript/CSS patterns
- Use modern ES6+ features appropriately
- Maintain accessibility standards (WCAG 2.1 AA)
- Document complex functionality

### Testing
- Test search functionality with various queries
- Verify filter combinations work correctly
- Ensure responsive design across devices
- Test keyboard navigation and accessibility

## 📄 License

This module is part of the Agentic RAG project and follows the same licensing terms.

---

**Built with ❤️ for the modern knowledge worker** 